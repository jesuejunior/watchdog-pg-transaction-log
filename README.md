# Watchdog PostgreSQL on RDS
## Usage
### Configuration

Create the secret on secret manager, both should be created as plain text.

The first one, must contains the user/pass for a user with superpower, because this user will be responsable to kill the replication PID and remove the replication slot.

__{dev,stg,prd}/RDS/DATABASE_URL__

```shell
postgresql://crm:abc1234@poc-db-aosudhasiye.amazon.com:5432/crm   
```

This is the data_stream password, during the configure db we have to create a user with strict permissions.

__{dev,stg,prd}/RDS/data_stream__

```shell
XXXX1234
```

### Deployment

In order to deploy the code, you need to run the following command:

```
$ serverless deploy --stage {dev,stg,prd}
```

After running deploy, you should see output similar to:

```bash
Deploying watchdog-data-stream to stage dev (us-east-1)


✔ Service deployed to stack watchdog-data-stream-dev (65s)


functions:
  simulator: watchdog-data-stream-dev-simulator (49 MB)
  configureDB: watchdog-data-stream-dev-configureDB (49 MB)
  transactionLog: watchdog-data-stream-dev-transactionLog (49 MB)
```

### Invocation

After successful deployment, you can invoke the deployed function by using the following command:

```shell
serverless invoke --function transactionLog
```

Which should result in response similar to the following:

```json
{
    "statusCode": 200,
    "body": "{\"message\": \"Function executed successfully!\", \"event\": {}}"
}
```

### Local development

You can invoke your function locally by using the following command:

```bash
serverless invoke local --function 
```

Which should result in response similar to the following:

```

```

### Bundling dependencies

In case you would like to include third-party dependencies, you will need to use a plugin called `serverless-python-requirements`. You can set it up by running the following command:

```bash
serverless plugin install -n serverless-python-requirements
```

Running the above will automatically add `serverless-python-requirements` to `plugins` section in your `serverless.yml` file and add it as a `devDependency` to `package.json` file. The `package.json` file will be automatically created if it doesn't exist beforehand. Now you will be able to add your dependencies to `requirements.txt` file (`Pipfile` and `pyproject.toml` is also supported but requires additional configuration) and they will be automatically injected to Lambda package during build process. For more details about the plugin's configuration, please refer to [official documentation](https://github.com/UnitedIncome/serverless-python-requirements).

To change the alarm settings and validate the trigger manually. Run
```shell
aws --profile XXX cloudwatch set-alarm-state --alarm-name "awsrds-poc-db-High-Transaction-Logs-Disk-Usage" --state-value ALARM  --state-reason "testing purposes"
```
