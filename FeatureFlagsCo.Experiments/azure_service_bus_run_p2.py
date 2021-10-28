import logging
from azure_service_bus.p2_azure_service_bus_get_expt_result import P2AzureGetExptResultReceiver
from config.config_handling import get_config_value

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%m-%d %H:%M')
    conn_str = get_config_value('azure', 'conn_str')
    redis_host = get_config_value('redis', 'redis_host')
    redis_port = get_config_value('redis', 'redis_port')
    redis_passwd = get_config_value('redis', 'redis_passwd')
    topic = get_config_value('p2', 'topic_Q2')
    subscription = get_config_value('p2', 'subscription_Q2')
    try:
        wait_timeout = float(get_config_value('p2', 'wait_timeout'))
    except:
        wait_timeout = 30.0
    P2AzureGetExptResultReceiver(conn_str, redis_host, redis_port, redis_passwd, wait_timeout).consume(
        (topic, subscription), is_dlq=False)
