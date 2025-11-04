import unittest
import pandas as pd

from ssda903.datacontainer import DemandModellingDataContainer

class TestRemoveRedundantEpisodes(unittest.TestCase):
    def test__remove_redundant_episodes(self):
        dummy = None

        # Test 1: 2 rows; 1 episode to keep and 1 redundant; non-null data in DEC, REC, REASON_PLACE_CHANGE moved up
        sample_1 = {
            "CHILD": [1,1],
            "DECOM": ["01/01/2020", "01/02/2020"],
            "DEC": ["01/02/2020", "01/03/2020"],
            "RNE": ["S", "L"],
            "REC": ["X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B"]
        }
        sample_1_df = pd.DataFrame(sample_1)
        sample_1_df["DECOM"] = pd.to_datetime(sample_1_df["DECOM"], format="%d/%m/%Y")
        sample_1_df["DEC"] = pd.to_datetime(sample_1_df["DEC"], format="%d/%m/%Y")

        test_result_1 = DemandModellingDataContainer._remove_redundant_episodes(dummy, sample_1_df)
        self.assertEqual(len(test_result_1),1)
        first_row = test_result_1.iloc[0]
        self.assertEqual(first_row["DEC"].strftime("%d/%m/%Y"),"01/03/2020")
        self.assertEqual(first_row["RNE"],"S")
        self.assertEqual(first_row["DECOM"].strftime("%d/%m/%Y"),"01/01/2020")
        self.assertEqual(first_row["REC"],"E15")
        self.assertEqual(first_row["REASON_PLACE_CHANGE"],"B")

        # Test 2: 3 rows; 2 episodes to keep and 1 redundant; null data in DEC moved up
        sample_2 = {
            "CHILD": [2,2,2],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020"],
            "DEC": ["01/02/2020", "01/03/2020", None],
            "RNE": ["S", "P", "T"],
            "REC": ["X", "X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B", "C"]
        }
        sample_2_df = pd.DataFrame(sample_2)
        sample_2_df["DECOM"] = pd.to_datetime(sample_2_df["DECOM"], format="%d/%m/%Y")
        sample_2_df["DEC"] = pd.to_datetime(sample_2_df["DEC"], format="%d/%m/%Y")

        test_result_2 = DemandModellingDataContainer._remove_redundant_episodes(dummy, sample_2_df)
        self.assertEqual(len(test_result_2),2)
        second_row = test_result_2.iloc[1]
        self.assertTrue(pd.isna(second_row["DEC"]))
        self.assertEqual(second_row["RNE"],"P")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"),"01/02/2020")
        self.assertEqual(second_row["REC"],"E15")
        self.assertEqual(second_row["REASON_PLACE_CHANGE"],"C")

        # Test 3: 3 rows; 2 children, 1 with only a "U" row (so can't be removed as only one), 1 with "U", "P" concurrent, none removed as "U" is first
        sample_3 = {
            "CHILD": [2,3,3],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020"],
            "DEC": ["01/02/2020", "01/03/2020", None],
            "RNE": ["U", "U", "B"],
            "REC": ["X", "X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B", "C"]
        }
        sample_3_df = pd.DataFrame(sample_3)
        sample_3_df["DECOM"] = pd.to_datetime(sample_3_df["DECOM"], format="%d/%m/%Y")
        sample_3_df["DEC"] = pd.to_datetime(sample_3_df["DEC"], format="%d/%m/%Y")

        test_result_3 = DemandModellingDataContainer._remove_redundant_episodes(dummy, sample_3_df)
        self.assertEqual(len(test_result_3),3)
        second_row = test_result_3.iloc[1]
        self.assertEqual(second_row["DEC"].strftime("%d/%m/%Y"),"01/03/2020")
        self.assertEqual(second_row["RNE"],"U")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"),"01/02/2020")
        self.assertEqual(second_row["REC"],"X")
        self.assertEqual(second_row["REASON_PLACE_CHANGE"],"B")

        # Test 4: 4 rows; 2 episodes to keep and 2 redundant; data from final row carried up
        sample_4 = {
            "CHILD": [4,4,4,4],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020", "01/04/2020"],
            "DEC": ["01/02/2020", "01/03/2020", "01/04/2020", "01/05/2020"],
            "RNE": ["S", "P", "T", "L"],
            "REC": ["X", "X", "X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B", "C", "D"]
        }
        sample_4_df = pd.DataFrame(sample_4)
        sample_4_df["DECOM"] = pd.to_datetime(sample_4_df["DECOM"], format="%d/%m/%Y")
        sample_4_df["DEC"] = pd.to_datetime(sample_4_df["DEC"], format="%d/%m/%Y")

        test_result_4 = DemandModellingDataContainer._remove_redundant_episodes(dummy, sample_4_df)
        self.assertEqual(len(test_result_4),2)
        second_row = test_result_4.iloc[1]
        self.assertEqual(second_row["DEC"].strftime("%d/%m/%Y"),"01/05/2020")
        self.assertEqual(second_row["RNE"],"P")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"),"01/02/2020")
        self.assertEqual(second_row["REC"],"E15")
        self.assertEqual(second_row["REASON_PLACE_CHANGE"],"D")

        # Test 5: 2 rows; 2 episodes to keep as "T" episode is non-contiguous with earlier "P" episode
        sample_5 = {
            "CHILD": [5,5],
            "DECOM": ["01/01/2020", "01/03/2020"],
            "DEC": ["01/02/2020", None],
            "RNE": ["P", "T"],
            "REC": ["X", "E15"],
            "REASON_PLACE_CHANGE": ["A", "B"]
        }
        sample_5_df = pd.DataFrame(sample_5)
        sample_5_df["DECOM"] = pd.to_datetime(sample_5_df["DECOM"], format="%d/%m/%Y")
        sample_5_df["DEC"] = pd.to_datetime(sample_5_df["DEC"], format="%d/%m/%Y")

        test_result_5 = DemandModellingDataContainer._remove_redundant_episodes(dummy, sample_5_df)
        self.assertEqual(len(test_result_5),2)
        first_row = test_result_5.iloc[0]
        self.assertEqual(first_row["DEC"].strftime("%d/%m/%Y"),"01/02/2020")
        self.assertEqual(first_row["RNE"],"P")
        self.assertEqual(first_row["DECOM"].strftime("%d/%m/%Y"),"01/01/2020")
        self.assertEqual(first_row["REC"],"X")
        self.assertEqual(first_row["REASON_PLACE_CHANGE"],"A")

        # Test 6: 3 rows; same child; first is "U" so can't be removed; second "U" is removed with info flowing to first, third "B" is not changed
        sample_6 = {
            "CHILD": [6,6,6],
            "DECOM": ["01/01/2020", "01/02/2020", "01/03/2020"],
            "DEC": ["01/02/2020", "01/03/2020", None],
            "RNE": ["U", "U", "B"],
            "REC": ["X", "E15", None],
            "REASON_PLACE_CHANGE": ["A", "B", "C"]
        }
        sample_6_df = pd.DataFrame(sample_6)
        sample_6_df["DECOM"] = pd.to_datetime(sample_6_df["DECOM"], format="%d/%m/%Y")
        sample_6_df["DEC"] = pd.to_datetime(sample_6_df["DEC"], format="%d/%m/%Y")

        test_result_6 = DemandModellingDataContainer._remove_redundant_episodes(dummy, sample_6_df)
        self.assertEqual(len(test_result_6),2)
        first_row = test_result_6.iloc[0]
        self.assertEqual(first_row["DEC"].strftime("%d/%m/%Y"),"01/03/2020")
        self.assertEqual(first_row["RNE"],"U")
        self.assertEqual(first_row["DECOM"].strftime("%d/%m/%Y"),"01/01/2020")
        self.assertEqual(first_row["REC"],"E15")
        self.assertEqual(first_row["REASON_PLACE_CHANGE"],"B")
        second_row = test_result_6.iloc[1]
        self.assertTrue(pd.isna(second_row["DEC"]))
        self.assertEqual(second_row["RNE"],"B")
        self.assertEqual(second_row["DECOM"].strftime("%d/%m/%Y"),"01/03/2020")
        self.assertTrue(pd.isna(second_row["REC"]))
        self.assertEqual(second_row["REASON_PLACE_CHANGE"],"C")