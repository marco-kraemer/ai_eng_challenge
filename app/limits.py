"""Process-local safeguards for the free, single-worker prototype."""
import math
import threading
import time
from collections import deque
from typing import Callable
from starlette.responses import JSONResponse
from starlette.types import ASGIApp, Scope, Receive, Send

class RateLimiter:
    def __init__(self,window=60,max_actors=1000,clock: Callable[[],float]=time.monotonic):
        self.window=window;self.max_actors=max_actors;self.clock=clock
        self.buckets: dict[str,deque] = {}
        self.lock=threading.Lock()

    def allow(self,key: str,limit: int) -> tuple[bool,int]:
        with self.lock:
            now=self.clock()
            for actor in list(self.buckets):
                while self.buckets[actor] and self.buckets[actor][0]<=now-self.window:self.buckets[actor].popleft()
                if not self.buckets[actor]:del self.buckets[actor]
            if key not in self.buckets and len(self.buckets)>=self.max_actors:
                del self.buckets[min(self.buckets,key=lambda actor:self.buckets[actor][-1])]
            bucket=self.buckets.setdefault(key,deque())
            if len(bucket)>=limit:return False,max(1,math.ceil(self.window-(now-bucket[0])))
            bucket.append(now)
            return True,0

class BodyLimitMiddleware:
    def __init__(self,app: ASGIApp,max_bytes: int=16000):self.app=app;self.max_bytes=max_bytes

    async def __call__(self,scope: Scope,receive: Receive,send: Send):
        if scope['type']!='http' or scope.get('method') not in ('POST','PUT','PATCH'):
            await self.app(scope,receive,send);return
        messages=[];size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect':return
            size+=len(message.get('body',b''))
            if size>self.max_bytes:
                await JSONResponse({'detail':'Mensagem muito grande. Reduza o conteúdo e tente novamente.'},status_code=413)(scope,receive,send)
                return
            messages.append(message)
            if not message.get('more_body',False):break
        async def replay():
            return messages.pop(0) if messages else await receive()
        await self.app(scope,replay,send)
