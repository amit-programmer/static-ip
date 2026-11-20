from locust import HttpUser, task, between
class DeltaUser(HttpUser):
    wait_between = between(0.5, 1)
    @task
    def health(self):
        self.client.get("/health")