CREATE EXTERNAL TABLE IF NOT EXISTS group_membership (
  namespace STRING,
  group STRING,
  user STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://admin-console-${account_id}/monitoring/quicksight/group_membership/'
TBLPROPERTIES (
  'areColumnsQuoted'='false',
  'classification'='csv',
  'columnsOrdered'='true',
  'compressionType'='none',
  'delimiter'=',',
  'typeOfData'='file'
);

CREATE EXTERNAL TABLE IF NOT EXISTS object_access (
  aws_region STRING,
  object_type STRING,
  object_name STRING,
  object_id STRING,
  principal_type STRING,
  principal_name STRING,
  namespace STRING,
  permissions STRING
)
ROW FORMAT DELIMITED
FIELDS TERMINATED BY ','
STORED AS INPUTFORMAT 'org.apache.hadoop.mapred.TextInputFormat'
OUTPUTFORMAT 'org.apache.hadoop.hive.ql.io.HiveIgnoreKeyTextOutputFormat'
LOCATION 's3://admin-console-${account_id}/monitoring/quicksight/object_access/'
TBLPROPERTIES (
  'areColumnsQuoted'='false',
  'classification'='csv',
  'columnsOrdered'='true',
  'compressionType'='none',
  'delimiter'=',',
  'typeOfData'='file'
);
