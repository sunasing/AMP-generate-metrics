# Generate Prometheus and OTEL metrics and collect them with Azure Managed Prometheus

This repo has a python app that generates Prometheus and OTEL metrics, and Kubernetes artifacts to run the app and collect metrics with Azure Managed Prometheus.

## Prerequisites

1. Install Docker Desktop
2. You need to have a docker repository - either in [DockerHub](https://hub.docker.com/) or Azure Container Registry. For this tutorial, we will use DockerHub.

## Steps

### Setting up Azure Managed Prometheus

Create an AKS cluster and enable Managed Prometheus and Grafana - This will enable Prometheus add-on on your AKS cluster, create an Azure Monitor Workspace and Azure Managed Grafana. Follow instructions here: [Enable Managed Prometheus on AKS cluster](https://learn.microsoft.com/azure/azure-monitor/containers/kubernetes-monitoring-enable?tabs=cli#enable-prometheus-and-grafana).

### Setting up the application

1. Clone the repository locally.
2. You will find the following files:
   - Application source code: prommetricsgenerate.py
   - Dockerfile and docker-compose.yaml -> to build the docker images
   - Deployment.yaml and service.yaml -> to deploy the app to the AKS cluster
   - servicemonitor.yaml -> to configure AMP to scrape metrics from the app
3. First build the docker image from the application source code:
   - docker build -t <imagename>:<tag>
   example: docker build -t esunayana/prometheus-metrics-app:latest .
4. Check if the image is available in your local Docker Desktop. You can also run the image and ensure no errors in the output.
5. Push the image to the Dockerhub repo, or any other repo:
   - docker push <dockerhubrepo>/imagename>:<tag>
   example: docker push esunayana/prometheus-metrics-app:latest

7. Now, apply the deployment.yaml and service.yaml to the AKS cluster. This will deploy the app to the AKS cluster.
   - kubectl apply -f deployment.yaml
   - kubectl apply -f service.yaml
   - kubectl apply -f servicemonitor.yaml

9. Check if the service is running: kubectl get service
10. port-forward the service to access the app:

    - kubectl port-forward service/prometheus-metrics-app 8000
    - http://localhost:8000
    
## Query and view metrics

Go to the Azure Managed Grafana or Azure Monitor workspace to query and view the app metrics that we add in our app.

1. On the Azure portal, go to the Azure Monitor Workspace instance and go to "Metrics".
2. Query for the metrics
