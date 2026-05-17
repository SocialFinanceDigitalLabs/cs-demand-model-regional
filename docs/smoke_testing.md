# Minimum Viable Product (MVP) Smoke Testing

This document outlines the smoke testing process for the Minimum Viable Product (MVP) of the CS Demand Model Regional application. Smoke testing is a preliminary testing phase that ensures the basic functionality of the application is working as expected before proceeding to more comprehensive testing.
## Test Cases
1. **User Authentication**
   - Test that users can successfully log in using SSO.
    - Verify that users without proper credentials cannot access the application beyond the home page.
2. **Data Upload**
   - Test that users can upload data files in the correct format.
    - Verify that the application handles incorrect file formats gracefully.
3. **Data Visualization**
   - Test that the generated results are visualized correctly in the application (Historic Data, Start Modelling, Adjust Forecast, Projecting Spend).
    - Verify that the visualizations are accurate and correspond to the processed data.
4. **Performance**
   - Test that the application responds within an acceptable time frame for key actions (e.g. login, data upload, loading analysis pages).
5. **Form Submission**
    - Test that forms (e.g., for adjusting forecasts) can be submitted successfully and that the application processes the input correctly (an expected change happens in the data visualisations).
6. **Scenario Management**
   - Test that user scenarios are managed correctly: Users can save and load scenarios.

### Further testing should be conducted beyond smoke testing to ensure the application is robust and ready for production. This includes unit testing, integration testing, and user acceptance testing (UAT). Consider what other critical functionalities should be included in the smoke testing based on the specific code updates to be released.