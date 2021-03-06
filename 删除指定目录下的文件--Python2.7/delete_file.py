#! /usr/bin/env python
# -*- coding: utf-8 -*-

from base64 import b64encode
import requests
import urllib
import Queue

# -----------------------
bucket = ''
username = ''
password = ''

path = ''
# -----------------------
queue = Queue.LifoQueue()
queue_list = Queue.LifoQueue()


def record_request(url, status):
    if status:
        with open('deleted_file_list.txt', 'a') as file:
            file.write(url + '\n')
    else:
        with open('list_failed_path.txt', 'a') as failed_file:
            failed_file.write(url + '\n')


def do_http_request(method, key, upyun_iter):
    uri = '/' + bucket + (lambda x: x[0] == '/' and x or '/' + x)(key)
    if isinstance(uri, unicode):
        uri = uri.encode('utf-8')
    uri = urllib.quote(uri)
    headers = {
        'Authorization': 'Basic ' + b64encode(username + ':' + password),
        'User-Agent': 'up-python-delete-script',
        'X-List-Limit': '300'
    }
    if method is not 'DELETE':
        if upyun_iter is not None or upyun_iter is not 'g2gCZAAEbmV4dGQAA2VvZg':
            headers['x-list-iter'] = upyun_iter

    url = "http://v0.api.upyun.com" + uri
    requests.adapters.DEFAULT_RETRIES = 5
    session = requests.session()
    try:
        response = session.request(method, url, headers=headers, timeout=30)
        status = response.status_code
        if status == 200 and method != 'DELETE':
            content = response.content
            try:
                iter_header = response.headers['x-upyun-list-iter']
            except Exception as e:
                iter_header = 'g2gCZAAEbmV4dGQAA2VvZg'
            data = {
                'content': content,
                'iter_header': iter_header
            }
            return data
        elif status == 200 and method == 'DELETE':
            return True
        else:
            print 'status: ' + str(status) + '--->' + url
            record_request(uri, False)
    except Exception as e:
        record_request(uri, False)


def getlist(key, upyun_iter):
    result = do_http_request('GET', key, upyun_iter)
    if not result:
        return None
    content = result['content']
    items = content.split('\n')
    content = [dict(zip(['name', 'type', 'size', 'time'],
                        x.split('\t'))) for x in items] + result['iter_header'].split()
    return content


def list_file_with_iter(path):
    upyun_iter = None
    while True:
        while upyun_iter != 'g2gCZAAEbmV4dGQAA2VvZg':
            res = getlist(path, upyun_iter)
            if res:
                upyun_iter = res[-1]
                for i in res[:-1]:
                    try:
                        if not i['name']:
                            if delete_file(path):
                                print 'folder deleted' + path
                            continue
                        new_path = path + i['name'] if path == '/' else path + '/' + i['name']
                        if i['type'] == 'F':
                            queue.put(new_path)
                            queue_list.put(new_path)
                        elif i['type'] == 'N':
                            result = delete_file(new_path)
                            print 'file deleted--->' + new_path
                            record_request(new_path, True)
                    except Exception as e:
                        print e
            else:
                if not queue.empty():
                    path = queue.get()
                    upyun_iter = None
                    queue.task_done()
        else:
            if not queue.empty():
                path = queue.get()
                upyun_iter = None
                queue.task_done()
            else:
                while not queue_list.empty():
                    delete_file(queue_list.get())
                    queue_list.task_done()
                break


def delete_file(key):
    return do_http_request('DELETE', key, None)


if __name__ == '__main__':
    list_file_with_iter(path)
    print "Job's Done!"
