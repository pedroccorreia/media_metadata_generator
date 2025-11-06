# Presentation Layer

## Purpose

This directory contains the presentation layer of the Media Metadata Generator application. It is responsible for providing the user interface and for interacting with the backend services.

## Architecture



The presentation layer consists of two main components:



*   **Frontend:** A Next.js application that provides the user interface.

*   **Backend:** An Express.js application that provides a simple API for the frontend to interact with.



The frontend and backend are deployed as two separate Cloud Run services. The frontend makes API calls to the backend to fetch data and to interact with the Genkit AI flows.



## Setup



Before deploying the application, you need to configure your Google Cloud project and your Firestore database.



### Project ID



The `deploy.sh` script uses the `gcloud` command-line tool to deploy the application. You need to make sure that you have authenticated with `gcloud` and that you have set the correct project ID. You can set the project ID using the following command:



```bash

gcloud config set project YOUR_PROJECT_ID

```



### Firestore Database



The backend service fetches data from a Firestore database. The name of the Firestore collection is configured in `presentation/ui-backend/server.js`. By default, the collection name is `media_assets`. You can change this to match the name of your Firestore collection.



## Deployment



To deploy the presentation layer, navigate to this directory and run the following command:



```bash

./deploy.sh

```



This script will:



1.  Build the Docker images for the frontend and backend.

2.  Push the images to Google Container Registry.

3.  Deploy the images to Cloud Run.
