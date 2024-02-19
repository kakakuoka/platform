import requests
import time
import os
import json


"""

When a Teams meeting is started, running the below script would do the following:
1) The Teams meeting bot will join the meeting and start recording
2) The script continuously checks the progress of the meeting and as the meeting ends, 
it sends the data for transcription to Voicegain servers.
3) The transcription results then get saved in the local output folder and 
can also be fetched via the platform console.

"""


platform = "ascalon"
JWT = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiI5Y2QxN2I0NS03MzI2LTRiODEtYTQzNi1jYThlOTgxOWYyNWMiLCJhdWQiOiIqLmFzY2Fsb24uYWkiLCJzdWIiOiIwMjA3YmUzYS1hNzA1LTQxZWMtYTM3Mi05MGQxNDQ2NDQ5ZjEifQ.4XCOTiHo7OE5p4w-EaC6MApxuV7CO_vVXsGbfh0IHuM"
headers = {"Authorization":JWT}
output_path = "output"
if not os.path.exists(output_path):
   os.mkdir(output_path)

progress_phase_dict = {
		"ACCEPTED": "request has been accepted",
		"WAITING": "waiting for the audio",
		"QUEUED": "request has been queued",
		"FETCHING": "fetching audio data",
		"FETCHED": "fetched audio data",
		"PROCESSING": "doing the recognition",
		"DONE": "recognition completed successfully",
		"STOPPED": "progress stopped by a user request",
		"RECOMPUTING": "reprocessing the transcript",
		"ERROR": "some error at any of the steps/phases"
}


"""
Make a post req to join meeting.
Replace the below values with your own data.
"""
body_asr_meeting_join = {
  "meetingPlatform": "teams",
  "participantName": "VoiceGain",
  "meetingUrl": "https://teams.microsoft.com/l/meetup-join/19:meeting_ZTI5ODJkZDAtNWIzNS00YThmLWIzMDgtNzg5OTdmY2ZhYjll@thread.v2/0?context=%7B%22Tid%22:%22b9a30004-c2c6-4ab8-ab9f-16c7c23835fb%22,%22Oid%22:%22ad51bcf6-6806-4a2f-8cce-987e2cd274c1%22%7D",
  "persistSeconds": 36000,
#  "audio": {
#	  "input": "Microphone (2 - Shure MV5)",
#	  "output": "Headphones (2 - Shure MV5)",
#  },
  "settings": {"asr":{"acousticModel":"VoiceGain-kappa:2","languages":["en-us"],"sensitivity":0.5,"speedVsAccuracy":0.5},"formatters":[{"type":"digits"},{"type":"basic","parameters":{"enabled":"true"}},{"type":"enhanced","parameters":{"CC":True,"EMAIL":"true"}},{"type":"profanity","parameters":{"mask":"partial"}},{"type":"spelling","parameters":{"lang":"en-US"}},{"type":"redact","parameters":{"CC":"partial","ZIP":"full","PERSON":"[PERSON]"}},{"type":"regex","parameters":{"pattern":"[1-9][0-9]{3}[ ]?[a-zA-Z]{2}","mask":"full","options":"IA"}}],"compliance":{"doNotLog":False}},
  "tags": [
    "meeting"
  ]
}

def asr_meeting_join_api():
	# Make the POST request with the json parameter
	url = "https://api."+platform+".ai/v1/asr/meeting/join"
	response = requests.post(url, json=body_asr_meeting_join, headers=headers)
	print('Response of POST asr/meeting/join: ', response.json())

	# Check the status code of the response
	if response.status_code == 200:
		print('POST asr/meeting/join request successful!')
	else:
		print('POST asr/meeting/join request failed. Status code:', response.status_code)

	print(response.headers)
	return response.json()



def get_asr_meeting_api(asr_meeting_join_response):

	if(asr_meeting_join_response.get("meetingSessionId")==None):
		print('Response does not have meeting id')
	else:
		meetingSessionId = asr_meeting_join_response["meetingSessionId"]
		while(True):
			get_meeting_status_url = "https://api." + platform + ".ai/v1/asr/meeting/" + meetingSessionId
			response = requests.get(get_meeting_status_url, headers=headers)
			print('Response of GET asr/meeting/{meeting-id}: ', response.json())

			# Check the status code of the response
			if response.status_code == 200:
				print('GET asr/meeting/{meeting-id} request successful!')
			else:
				print('GET asr/meeting/{meeting-id} request failed. Status code:', response.status_code)

			progress_phase = response.json()["progress"]["phase"]
			print("The progress phase is {}, {}".format(progress_phase, progress_phase_dict[progress_phase]))

			if(progress_phase=="DONE" or progress_phase=="ERROR"):
				return response.json()

			time.sleep(10)

def get_transcript(response):
	transcript = ""
	words_list = response["words"]

	for words in words_list:
		word_list_inside = words["words"]
		for word in word_list_inside:
			transcript = transcript + word["utterance"] + " "

	return transcript;


def write_transcript_into_file(transcript, meetingSessionId):

	response_path = os.path.join(output_path, "{}.json".format(meetingSessionId))
	with open(response_path, 'w') as outfile:
		json.dump(transcript, outfile)

	print("Save final transcription result to {}".format(response_path), flush=True)


def get_asr_meeting_data_api(asr_meeting_join_response):

	if(asr_meeting_join_response.get("meetingSessionId")==None):
		print('Response does not have meeting id')
	else:
		meetingSessionId = asr_meeting_join_response["meetingSessionId"]
		get_meeting_status_url = "https://api." + platform + ".ai/v1/asr/meeting/" + meetingSessionId + "/data?words=true"
		response = requests.get(get_meeting_status_url, headers=headers)
		print('Response of GET asr/meeting/{meeting-id}/data/: ', response.json())

		# Check the status code of the response
		if response.status_code == 200:
			print('GET asr/meeting/{meeting-id}/data/ request successful!')
			transcript = get_transcript(response.json())
			write_transcript_into_file(transcript, meetingSessionId)

		else:
			print('GET asr/meeting/{meeting-id}/data/ request failed. Status code:', response.status_code)


def start_meeting_flow():
	post_asr_meeting_join_response = asr_meeting_join_api()
	get_asr_meeting_response = get_asr_meeting_api(post_asr_meeting_join_response)
	get_asr_meeting_response = get_asr_meeting_data_api(post_asr_meeting_join_response)



if __name__ == "__main__":
	start_meeting_flow()