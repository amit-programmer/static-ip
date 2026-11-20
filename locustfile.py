from locust import HttpUser, task, between

class DeltaUser(HttpUser):
    wait_between = between(1, 2)

    @task(3)
    def health(self):
        self.client.get("/health")

    @task(1)
    def test_ip(self):
        self.client.get("/test-ip")