# Run Helm Chart

You will need:

- Python
- Docker
- Helm

## Build Docker Image

To build the Docker image for the os-vim-driver from this repository, do the following:

1. Build a python whl for the driver

```
python3 setup.py bdist_wheel
```

2. Move the whl now in `dist` to the `docker/whl` directory (ensure no additional whls are in the docker directory)

```
cp dist/os_vim_driver-<driver-version>-py3-none-any.whl docker/whls/
```

If using a development version (`.dev` version) of Ignition (check `osvimdriver/pkg_info.json`) then you need to build and copy the Ignition whl to the `docker/whls` directory as well.

3. Navigate to the `docker` directory

```
cd docker
```

4. Build the docker image

```
docker build -t accanto/os-vim-driver:<driver-version> .
```

## Run Helm Chart

Run the helm chart, setting the Docker image version if different to the default in `helm/os-vim-driver/values.yaml`:

```
helm install helm/os-vim-driver --name os-vim-driver --set docker.version=<driver-version>
```

By default, the driver will attempt to connect to Kafka with the address `alm-kafka:9092`.  For [All In One](https://github.com/accanto-systems/lm-allinone) it should be set to `foundation-kafka:9092`:

```
helm install helm/os-vim-driver --name os-vim-driver --set app.config.override.messaging.connection_address=foundation-kafka:9092
```

# Access Swagger UI

The Swagger UI can be found at `http://your_host:31681/api/infrastructure/ui` e.g. `http://localhost:31681/api/infrastructure/ui`
