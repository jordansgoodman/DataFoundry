import os
import dlt
import pandas as pd

DEFAULT_URL = "https://d37ci6vzurychx.cloudfront.net/trip-data/yellow_tripdata_2023-01.parquet"

@dlt.resource(name="nyc_taxi_yellow_tripdata", write_disposition="replace")
def nyc_taxi():
    url = os.environ.get("NYC_TAXI_URL", DEFAULT_URL)
    df = pd.read_parquet(url)
    df.columns = [c.lower() for c in df.columns]
    yield df


def run():
    pipeline = dlt.pipeline(
        pipeline_name="nyc_taxi",
        destination="postgres",
        dataset_name="analytics",
    )
    load_info = pipeline.run(nyc_taxi())
    print(load_info)

if __name__ == "__main__":
    run()
