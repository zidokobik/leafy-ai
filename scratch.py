import asyncio

import aioboto3
from cachetools import TTLCache
from cachetools_async import cached
from httpx import AsyncClient
from icecream import ic

username = "student"
password = "Leafy1237"
client_id = "697e8fi74idktf13lb34hresjm"

url = "https://hrfhf8qlce.execute-api.ap-southeast-2.amazonaws.com/images/student/latest"


@cached(cache=TTLCache(maxsize=1, ttl=3599))
async def get_access_token():
	session: aioboto3.Session = aioboto3.Session()
	async with session.client("cognito-idp", region_name="ap-southeast-2") as cognito_client:
		response = await cognito_client.initiate_auth(
			ClientId=client_id,
			AuthFlow="USER_PASSWORD_AUTH",
			AuthParameters={
				"USERNAME": username,
				"PASSWORD": password,
			},
		)
		ic(response)
		return response["AuthenticationResult"]["AccessToken"]


async def main():
	access_token = await get_access_token()
	ic(access_token)

	# async with AsyncClient(http2=True) as client:
	# 	while True:
	# 		# url = "https://hrfhf8qlce.execute-api.ap-southeast-2.amazonaws.com/images/student/archive?camera=level1_camera1"
	# 		resp = await client.get(url, headers={"Authorization": f"Bearer {access_token}"})
	# 		data = resp.json()
	# 		ic(data)
	# 		return

	# 		camera_url = data["images"][0]["url"]
	# 		ic(camera_url)

	# 		resp = await client.get(camera_url)
	# 		with open("latest_image.jpg", "wb+") as f:
	# 			f.write(resp.content)
	# 		ic(len(resp.content))

	# 		await asyncio.sleep(1)


if __name__ == "__main__":
	try:
		import uvloop
	except ImportError:
		loop_factory = asyncio.new_event_loop
	else:
		loop_factory = uvloop.new_event_loop
	with asyncio.Runner(loop_factory=loop_factory) as runner:
		runner.run(main())
