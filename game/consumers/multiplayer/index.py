from channels.generic.websocket import AsyncWebsocketConsumer
import json
from django.conf import settings
from django.core.cache import cache

class MultiPlayer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = None

        for i in range(1000):
            name = "room-%d" % (i)
            if not cache.has_key(name) or len(cache.get(name)) < settings.ROOM_CAPACITY:
                self.room_name = name
                break

        if not self.room_name:
            return

        await self.accept()

        if not cache.has_key(self.room_name):
            cache.set(self.room_name, [], 3600) # validity is 1 hour

        for player in cache.get(self.room_name):
            await self.send(text_data = json.dumps({
                'event': "create_player",
                'uuid': player['uuid'],
                'username': player['username'],
                'photo': player['photo'],
            }))

        await self.channel_layer.group_add(self.room_name, self.channel_name) # a group api in Django channels which have many function to call

    async def disconnect(self, close_code): # this function is not necessarily called, so that you'd better not count the number of people
        print('disconnect')
        await self.channel_layer.group_discard(self.room_name, self.channel_name)

    async def create_player(self, data):
        players = cache.get(self.room_name)
        players.append({
            'uuid': data['uuid'],
            'username': data['username'],
            'photo': data['photo'],
        })
        cache.set(self.room_name, players, 3600) # validity is 1 hour
        await self.channel_layer.group_send( # mass texting
            self.room_name,
            {
                'type': "group_send_event", # meaning to send to everyone in the group
                'event': "create_player",
                'uuid': data['uuid'],
                'username': data['username'],
                'photo': data['photo'],
            }
        )

    async def group_send_event(self, data):
        await self.send(text_data = json.dumps(data))

    async def move_to(self, data):
        await self.channel_layer.group_send(
            self.room_name,
            {
                'type': "group_send_event",
                'event': "move_to",
                'uuid': data['uuid'],
                'tx': data['tx'],
                'ty': data['ty'],
            }

        )

    async def receive(self, text_data): # receive request from front-end
        data = json.loads(text_data) # json to dict
        event = data['event']
        if event == "create_player":
            await self.create_player(data)
        elif  event == "move_to":
            await self.move_to(data)

