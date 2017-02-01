# -*- coding: utf-8 -*-
import datetime
import json
import os

import freezegun


def write_local(path, data=''):
    parent = os.path.dirname(path)
    if not os.path.exists(parent):
        os.makedirs(parent)
    with open(path, 'w') as fp:
        fp.write(data)


def set_local_contents(client, key, timestamp=None, data=''):
    path = os.path.join(client.path, key)
    write_local(path, data)
    if timestamp is not None:
        os.utime(path, (timestamp, timestamp))


def set_local_index(client, data):
    with open(client.index_path(), 'w') as fp:
        json.dump(data, fp)
    client.reload_index()


def write_s3(boto, bucket, key, data=''):
    boto.put_object(
        Bucket=bucket,
        Key=key,
        Body=data,
    )


def set_s3_contents(s3_client, key, timestamp=None, data=''):
    if timestamp is None:
        freeze_time = datetime.datetime.utcnow()
    else:
        freeze_time = datetime.datetime.utcfromtimestamp(timestamp)

    with freezegun.freeze_time(freeze_time):
        write_s3(s3_client.boto, s3_client.bucket, os.path.join(s3_client.prefix, key), data)


def set_s3_index(s3_client, data):
    s3_client.boto.put_object(
        Bucket=s3_client.bucket,
        Key=os.path.join(s3_client.prefix, '.index'),
        Body=json.dumps(data),
    )
    s3_client.reload_index()
