import ai
import ai.ui.ai_sdk
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from icecream import ic
from pydantic import BaseModel

from .water_sensor import WaterSendorReadings

router = APIRouter()


@ai.tool
async def get_sensor_data() -> WaterSendorReadings:
	"""
	Get the latest water sensor readings of the farm.
	"""
	# TODO: This is a mock response for water sensor readings.
	return WaterSendorReadings(
		device="WaterSensors",
		ph=8.034,
		ec=1049,
		ec_units="uS/cm",
		ph_units="pH",
		ph_raw="8.034",
		ec_raw="1049,566,0.52,1.001",
		ph_valid=True,
		ec_valid=True,
		ph_error=None,
		ec_error=None,
		ph_status="success",
		ec_status="success",
		ph_response_code=1,
		ec_response_code=1,
		measurement_duration_ms=1010,
		uptime_ms=78103065,
		wifi_rssi_dbm=-37,
		ip="192.168.1.100",
		hostname="WaterSensors.local",
	).model_dump()


@ai.tool
async def control_irrigation_pump(on: bool) -> str:
	"""
	Turn the irrigation pump on or off.
	"""
	# TODO: This is a mock response for turning the irrigation pump on or off.
	return "Irrigation pump turned " + ("on" if on else "off")


@ai.tool
async def control_fan(on: bool) -> str:
	"""
	Turn the fan on or off.
	"""
	# TODO: This is a mock response for turning the fan on or off.
	return "Fan turned " + ("on" if on else "off")


# TODO: more tools


class ChatRequest(BaseModel):
	messages: list[ai.ui.ai_sdk.UIMessage]


@router.post("/chat")
async def chat(request: ChatRequest) -> StreamingResponse:
	# See https://ai-sdk.dev/docs/ai-sdk-ui/stream-protocol
	# See https://ai-python.dev/docs/basics/ai-sdk-ui

	messages, approvals = ai.ui.ai_sdk.to_messages(request.messages)
	ic(messages)

	ai.ui.ai_sdk.apply_approvals(approvals)

	# model = ai.get_model("inclusionai/ling-3.0-tiny-free")  # free model atm
	model = ai.get_model("openai/gpt-5-nano")

	chat_agent = ai.Agent(
		tools=[
			get_sensor_data,
			control_irrigation_pump,
			control_fan,
		]
	)

	async def stream_response():
		async with chat_agent.run(model, messages) as stream:
			async for chunk in ai.ui.ai_sdk.to_sse(stream):
				yield chunk

	return StreamingResponse(
		stream_response(),
		headers=ai.ui.ai_sdk.UI_MESSAGE_STREAM_HEADERS,
	)
