import logging
from azure_service_bus.azure_bus_health_check import AzureHealthCheck
from redismq.redis_health_check import RedisHealthCheck
from config.config_handling import get_config_value

if __name__ == '__main__':
    logging.basicConfig(level=logging.ERROR,
                        format='%(asctime)s,%(msecs)d %(levelname)-8s [%(filename)s:%(lineno)d] %(message)s',
                        datefmt='%m-%d %H:%M')
    engine = get_config_value('general', 'engine')
    redis_host = get_config_value('redis', 'redis_host')
    redis_port = get_config_value('redis', 'redis_port')
    redis_passwd = get_config_value('redis', 'redis_passwd')
    try:
        redis_ssl = bool(get_config_value('redis', 'redis_ssl'))
        wait_timeout = float(get_config_value('p2', 'wait_timeout'))
    except:
        redis_ssl = False
        wait_timeout = 30.0
    if engine == 'azure':
        AzureHealthCheck(redis_host, redis_port, redis_passwd, wait_timeout).check_health()
    elif engine == 'redis':
        RedisHealthCheck(redis_host, redis_port, redis_passwd, redis_ssl, wait_timeout).check_health()
    else:
        RedisHealthCheck(redis_host, redis_port, redis_passwd, redis_ssl, wait_timeout).check_health()
