import asyncio
import aiohttp
import http.client
import os,sys
import time
import logging


def catenate_data(text,data):
    text += "HTTP/1.1 {} {}\n".format(
        data['status'],
        http.client.responses[data['status']]
        )
    text += "\n".join(
        '{}:{}'.format(k,v) 
        for k,v in data['headers'].items()
    )
    return text

async def fetch(session,url,conf):
    """
    Сопрограмма для получения данных по указанному url
    """
    
    data = dict.fromkeys(['error','url','status','headers'])
    try:
        with aiohttp.Timeout(conf.timeout, loop=session.loop):    
            async with session.get(url,headers=conf.headers) as r:
                status = r.status
                headers = r.headers
                data.update(
                    {'url':url,
                    'status':status,
                    'headers':headers
                    })   
    
    except asyncio.TimeoutError as err:
        print('-' * 20  + "\n")
        conf.log.error('Fetch => %s|%s',str(err),url)
        data.update(
            {'error':str(err),'url':url}
        )
        
    except Exception as err:
        print('-' * 20  + "\n")
        conf.log.error('Fetch => %s|%s',str(err),url)
        data.update(
            {'error':str(err),'url':url}
        )
    
    return data

# продюсер без ожидания всех корутин
async def producer(conf):
    """Создает группу сопрограмм"""
    
    with open(conf.dest,'a') as dest:
        # создаем экземпляр клиента
        async with aiohttp.ClientSession() as session:
            # создаем задания
            tasks = [conf.loop.create_task(fetch(session,url,conf)) 
                for url in conf.urls
            ]
            # итерация по заданиям не ожидая завершения всех
            for task in asyncio.as_completed(tasks):
                data = await task
                text = '-' * 20  + "\n"
                try:
                    text += data['url'] +'\n'
                    if data['error'] is not None:
                         text += "ERROR:{}".format(data['error'])
                    else:
                        # если ошибок подключения не было
                        text = catenate_data(text,data)
                except Exception as err:
                    conf.log.error(" ".join([str(err),str(data)]))
                else:
                    print(text)
                    dest.write(text + '\n')

# продьюсер с ожиданием всех корутин
async def producer2(conf):
    """Создает группу сопрограмм"""
    
    with open(conf.dest,'a') as dest:
        # создаем экземпляр клиента
        async with aiohttp.ClientSession() as session:
            # создаем корутины
            coroutines = [fetch(session,url,conf) for url in conf.urls]
            # ожидаем завершения корутин
            # return_exceptions возврат исключений как объектов; 
            # то есть в корутинах они не поднимаются
            completed = await asyncio.gather(
                *coroutines,
                return_exceptions=conf.return_exceptions
            ) 
            
            for data in completed:
                text = '-' * 20  + '\n'
                
                try:
                    if isinstance(data,Exception):
                        text += "ERROR:{}".format(str(data))
                    else:
                        text += data['url'] +'\n'
                        if data['error'] is not None:
                             text += "ERROR:{}".format(data['error'])
                        else:
                            # если ошибок подключения не было
                            text = catenate_data(text,data)
                except Exception as err:
                    conf.log.error(" ".join([str(err),str(data)]))
                else:
                    print(text) # вывод на консоль
                    dest.write(text + '\n')

class Config():

    def __init__(self,
        argv,
        timeout=2,
        format='%(asctime)s %(levelname)s:%(message)s',
        return_exceptions=True
        ):
        self.argv = argv
        self.headers = {
                'Connection':'keep-alive',
                'User-Agent':
                    'Mozilla/5.0 (Windows NT 6.1)' 
                    'AppleWebKit/537.36 (KHTML, like Gecko)' 
                    'Chrome/58.0.3029.110 Safari/537.36 OPR/45.0.2552.898',
                'Accept':
                    'text/html,application/xhtml+xml,'
                    'application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Encoding':'gzip, deflate, lzma, sdch',
                'Accept-Language':'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
                'Upgrade-Insecure-Requests':'1',
                'DNT':'1',
               }
        self.return_exceptions = return_exceptions
        self.timeout = timeout # таймаут (в сек.) ожидания ответа от сервера
        self.source = argv[1] if len(argv) > 1 else "ip_list.txt"  # файл источник данных
        self.dest = argv[2] if len(argv) > 2 else "dest.txt"       # файл для записи данных
        self.format = format
        self.log = logging.getLogger(__name__)
        self.urls = [ip.strip() for ip in open(self.source)] 
        # получаем экземпляр цикла событий
        self.loop = asyncio.get_event_loop()
        
        logging.basicConfig(format=self.format, level=logging.INFO)

    
def main(argv):
    
    conf = Config(argv)
   
    conf.log.info("Start")
    try:
        # запуск цикла  обработки событий 
        conf.loop.run_until_complete(
            producer(conf)
        )

    except Exception as err:
        conf.log.error('Main => %s', str(err))
    
    finally:
        # закрываем цикл
        conf.loop.close() 
    conf.log.info("The End")


if __name__ == '__main__':
    
    main(sys.argv)
    # можно запускать с аргументами
    # python proxy_checker.py ip_list.txt dest2.txt
