from datetime import date
from typing import Literal, Optional

import click
import pandas as pd
import numpy as np
from click import style
from dateutil.relativedelta import relativedelta

from ssda903 import DemandModellingDataContainer
from ssda903.config import Config
from ssda903.datastore import fs_datastore

try:
    import matplotlib.pyplot as pp
except ImportError:
    pp = None


from demand_model import StockAndFlowPredictor, MultinomialPredictor
from ssda903.population_stats import PopulationStats


def style_prop(value, fg="green", bold=True, **kwargs):
    if hasattr(value, "strftime"):
        value = value.strftime("%Y-%m-%d")

    return style(value, fg=fg, bold=bold, **kwargs)


def plot_option(*args, help=None, **kwargs):
    if not pp:
        help = "Requires matplotlib"
    return click.option(*args, help=help, **kwargs)


class CliSetup:
    def __init__(self, source: str, start: date = None, end: date = None):
        self.config = Config()
        self.datastore = fs_datastore(source)
        self.dc = DemandModellingDataContainer(self.datastore, self.config)
        self.stats = PopulationStats(self.dc.enriched_view, self.config)

        # The default start date in 6m before the end of the dataset
        if start is None:
            start = self.dc.end_date - relativedelta(months=6)

        # The default end date is the end of the dataset
        if end is None:
            end = self.dc.end_date

        self.start = start
        self.end = end


@click.group()
def cli():
    pass


@cli.command()
@click.argument("source")
def list_files(source: str):
    """
    Opens SOURCE and lists the available files and metadata. This is for testing of source folders.
    """
    ds = fs_datastore(source)
    files = sorted(ds.files, key=lambda x: (x.metadata.year, x.metadata.name))
    for file in files:
        click.secho(f"{file.name}", fg="green", bold=True)
        click.secho(f"  Year: {click.style(file.metadata.year, fg='blue')}")
        if file.metadata.table:
            click.secho(f"  Table: {click.style(file.metadata.table, fg='blue')}")
        else:
            click.secho(f"  Table: {click.style('UNKNOWN', fg='red')}")
        click.secho(f"  Size: {click.style(file.metadata.size, fg='blue')}")
        click.echo()


@cli.command()
@click.argument("source")
@click.option("--start", "-s", type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", "-e", type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--export", type=click.Path(writable=True))
def analyse(source: str, start: date, end: date, export):
    """
    Opens SOURCE and runs analysis on the data between START and END. SOURCE can be a file or a filesystem URL.
    """
    setup = CliSetup(source, start, end)
    stats = PopulationStats(setup.dc.to_model, tuple())
    click.echo(
        f"Running analysis between {style_prop(setup.start)} and {style_prop(setup.end)})"
    )
    click.echo("Transition rates:")
    click.echo(stats.raw_transition_rates(setup.start, setup.end))

    if export:
        stats.to_excel(export, setup.start, setup.end)
        click.echo(f"Saved analysis to {style_prop(export)}")


@cli.command()
@click.argument("source")
@click.option(
    "--model",
    "-m",
    type=click.Choice(["stock_and_flow", "multinomial"]),
    default="multinomial",
    help="The model to use",
)
@click.option("--start", "-s", type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--end", "-e", type=click.DateTime(formats=["%Y-%m-%d"]))
@click.option("--prediction_date", "--pd", type=click.DateTime(formats=["%Y-%m-%d"]))
@plot_option("--plot", "-p", is_flag=True, help="Plot the results")
@click.option(
    "--standard_deviations",
    "--sd",
    type=int,
    default=None,
    help="Number of standard deviations to plot",
)
@click.option("--export", type=click.Path(writable=True))
def predict(
    source: str,
    model: Literal["stock_and_flow", "multinomial"],
    start: date,
    end: date,
    prediction_date: date,
    plot: bool,
    standard_deviations: Optional[int],
    export,
):
    if model == "stock_and_flow":
        predict_stock_and_flow(source, start, end, prediction_date, plot, export)
    else:
        predict_multinomial(source, start, end, prediction_date, plot, standard_deviations, export)


def predict_stock_and_flow(
    source: str, start: date, end: date, prediction_date: date, plot: bool, export
):
    """
    Analyses SOURCE between start and end, and then predicts the population at prediction_date.
    """
    setup = CliSetup(source, start, end)
    start, end = setup.start, setup.end

    if prediction_date is None:
        prediction_date = end + relativedelta(months=12)

    click.echo(
        f"Running analysis between {style_prop(setup.start)} and {style_prop(setup.end)} "
        f"and predicting to {style_prop(prediction_date)}"
    )
    predictor = StockAndFlowPredictor(
        population=setup.stats.stock_at(end),
        transition_rates=setup.stats.raw_transition_rates(start, end),
        transition_numbers=setup.stats.daily_entrants(start, end),
        start_date=end,
        external_bin_identifier=tuple(),
    )

    prediction_days = (prediction_date - end).days
    predicted_pop = predictor.predict(prediction_days, progress=True)
    historic_pop = setup.stats.stock.loc[:end]
    if export:
        predicted_pop.to_excel(export)
        click.echo(f"Saved prediction to {style_prop(export)}")

    if plot:
        if not pp:
            click.secho("Plotting requires matplotlib", fg="red")
        else:
            historic_pop = setup.stats.stock.loc[:end]

            pd.concat([historic_pop, predicted_pop], axis=0).plot()
            pp.axvline(end, alpha=0.4)
            pp.axvspan(start, end, alpha=0.1)
            pp.show()


def predict_multinomial(
    source: str,
    start: date,
    end: date,
    prediction_date: date,
    plot: bool,
    standard_deviations: int,
    export,
):
    """
    Analyses SOURCE between start and end, and then predicts the population at prediction_date.
    """
    setup = CliSetup(source, start, end)
    start, end = setup.start, setup.end

    if prediction_date is None:
        prediction_date = end + relativedelta(months=12)

    click.echo(
        f"Running analysis between {style_prop(setup.start)} and {style_prop(setup.end)} "
        f"and predicting to {style_prop(prediction_date)}"
    )
    predictor = MultinomialPredictor(
        population=setup.stats.stock_at(end),
        transition_rates=setup.stats.raw_transition_rates(start, end),
        transition_numbers=setup.stats.daily_entrants(start, end),
        start_date=end,
    )

    prediction_days = (prediction_date - end).days
    result = predictor.predict(prediction_days, progress=True)
    columns = [c for c in result.population.columns if "NOT_IN_CARE" not in c]

    predicted_pop = result.population[columns]
    variance = result.variance[columns]
    if export:
        joined_df = predicted_pop.join(variance, rsuffix="_variance")
        joined_df.to_excel(export)
        click.echo(f"Saved prediction to {style_prop(export)}")

    if plot:
        if not pp:
            click.secho("Plotting requires matplotlib", fg="red")
        else:
            historic_pop = setup.stats.stock.loc[:end]
            if not standard_deviations:
                pd.concat([historic_pop, predicted_pop], axis=0).plot()
                pp.axvline(end, alpha=0.4)
                pp.axvspan(start, end, alpha=0.1)
                pp.show()

            else:
                predicted_pop["total"] = predicted_pop.sum(axis=1)
                historic_pop["total"] = historic_pop.sum(axis=1)

                def get_standard_deviation(x):
                    for _ in range(standard_deviations):
                        x = np.sqrt(x)
                    return x

                confidence_intervals = variance.applymap(
                    lambda x: get_standard_deviation(x)
                )
                confidence_intervals["total"] = confidence_intervals.sum(axis=1)
                
                df_plot = pd.concat(
                    [predicted_pop["total"], confidence_intervals["total"]], axis=1
                )
                df_plot.columns = ["average", "standard_deviation"]
                df_plot["upper"] = df_plot["average"] + df_plot["standard_deviation"]
                df_plot["lower"] = df_plot["average"] - df_plot["standard_deviation"]
                df_plot["date"] = df_plot.index
                pp.plot(
                    historic_pop.index,
                    historic_pop.total,
                    label="Historical population",
                )

                # Plot predicted population with upper and lower uncertainty bounds
                pp.plot(
                    df_plot["date"], df_plot["average"], label="Predicted population"
                )
                pp.plot(
                    df_plot["date"],
                    df_plot["upper"],
                    label="Upper uncertainty bound",
                    linestyle="--",
                )
                pp.plot(
                    df_plot["date"],
                    df_plot["lower"],
                    label="Lower uncertainty bound",
                    linestyle="--",
                )
                pp.axvline(end, alpha=0.4)
                pp.axvspan(start, end, alpha=0.1)

                # Set labels and title
                pp.xlabel("Date")
                pp.ylabel("Population")
                pp.title("Total population prediction over time")

                # Add legend
                pp.legend()

                # Show the plot
                pp.show()
