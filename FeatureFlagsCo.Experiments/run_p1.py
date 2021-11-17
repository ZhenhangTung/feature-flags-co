import logging
import os
import sys

from azure_service_bus.azure_service_bus_experiment_imp import \
    P1AzureGetExptRecordingInfoReceiver as aure_sb_p1
from config.config_handling import get_config_value
from redismq.redis_experiment_imp import P1RedisGetExptRecordingInfoReceiver as redis_p1

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%m-%d %H:%M')
    engine = get_config_value('general', 'engine')
    sb_host = get_config_value('azure', 'fully_qualified_namespace')
    sb_sas_policy = get_config_value('azure', 'sas_policy')
    sb_sas_key = get_config_value('azure', 'servicebus_sas_key')
    redis_host = get_config_value('redis', 'redis_host')
    redis_port = get_config_value('redis', 'redis_port')
    redis_passwd = get_config_value('redis', 'redis_passwd')
    topic = get_config_value('p1', 'topic_Q1')
    subscription = get_config_value('p1', 'subscription_Q1')
    try:
        redis_ssl = bool(get_config_value('redis', 'redis_ssl'))
        prefetch_count = int(get_config_value('p1', 'prefetch_count'))
    except:
        redis_ssl = False
        prefetch_count = 1
    process_name = ''
    if len(sys.argv) > 1:
        process_name = sys.argv[1]
    else:
        process_name = os.path.basename(__file__)
    if engine == 'azure':
        aure_sb_p1(sb_host, sb_sas_policy, sb_sas_key, redis_host, redis_port, redis_passwd) \
            .consume(process_name=process_name,
                     topic=(topic, subscription),
                     prefetch_count=prefetch_count,
                     is_dlq=False)
    elif engine == 'redis':
        redis_p1(redis_host, redis_port, redis_passwd, redis_ssl).consume(process_name=process_name, topic=topic)
    else:
        redis_p1(redis_host, redis_port, redis_passwd, redis_ssl).consume(process_name=process_name, topic=topic)
