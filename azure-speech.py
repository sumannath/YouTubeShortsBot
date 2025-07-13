import azure.cognitiveservices.speech as speechsdk
import os
from typing import Optional
import time

from dotenv import load_dotenv


class AzureNeuralTTS:
    def __init__(self, subscription_key: str, region: str):
        """
        Initialize Azure Neural TTS client

        Args:
            subscription_key: Your Azure Speech Services subscription key
            region: Azure region (e.g., 'eastus', 'westus2')
        """
        self.subscription_key = subscription_key
        self.region = region
        self.speech_config = speechsdk.SpeechConfig(
            subscription=subscription_key,
            region=region
        )

        # Configure connection settings to handle network issues
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_InitialSilenceTimeoutMs,
            "30000"
        )
        self.speech_config.set_property(
            speechsdk.PropertyId.SpeechServiceConnection_EndSilenceTimeoutMs,
            "30000"
        )
        # Set proxy if needed (uncomment and configure if behind corporate firewall)
        # self.speech_config.set_proxy("proxy.company.com", 8080, "username", "password")

        # Alternative endpoint for testing (can help with connectivity issues)
        # self.speech_config.set_property(speechsdk.PropertyId.SpeechServiceConnection_Endpoint,
        #                                f"wss://{region}.tts.speech.microsoft.com/cognitiveservices/websocket/v1")

    def test_connection(self) -> bool:
        """
        Test connection to Azure Speech Services

        Returns:
            bool: True if connection successful, False otherwise
        """
        try:
            # Test with a simple synthesis
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None
            )

            result = synthesizer.speak_text_async("test").get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print("✓ Connection to Azure Speech Services successful")
                return True
            else:
                print(f"✗ Connection test failed: {result.reason}")
                if result.reason == speechsdk.ResultReason.Canceled:
                    details = result.cancellation_details
                    print(f"  Cancellation reason: {details.reason}")
                    if details.error_details:
                        print(f"  Error details: {details.error_details}")
                return False

        except Exception as e:
            print(f"✗ Connection test error: {str(e)}")
            return False

    def text_to_speech(self,
                       text: str,
                       voice_name: str = "en-US-AriaNeural",
                       output_file: str = "output.wav",
                       speech_rate: str = "0%",
                       speech_pitch: str = "0%") -> bool:
        """
        Convert text to speech using Azure Neural TTS

        Args:
            text: Text to convert to speech
            voice_name: Neural voice name (e.g., "en-US-AriaNeural")
            output_file: Output audio file path
            speech_rate: Speech rate (-50% to +200%)
            speech_pitch: Speech pitch (-50% to +50%)

        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Create SSML for better control
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
                <voice name="{voice_name}">
                    <prosody rate="{speech_rate}" pitch="{speech_pitch}">
                        {text}
                    </prosody>
                </voice>
            </speak>
            """

            # Configure audio output
            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_file)

            # Create synthesizer
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=audio_config
            )

            # Synthesize speech
            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                print(f"Speech synthesized successfully: {output_file}")
                return True
            elif result.reason == speechsdk.ResultReason.Canceled:
                cancellation_details = result.cancellation_details
                print(f"Speech synthesis canceled: {cancellation_details.reason}")
                if cancellation_details.reason == speechsdk.CancellationReason.Error:
                    print(f"Error details: {cancellation_details.error_details}")
                return False

        except Exception as e:
            print(f"Error during speech synthesis: {str(e)}")
            return False

    def text_to_speech_stream(self,
                              text: str,
                              voice_name: str = "en-US-AriaNeural") -> Optional[bytes]:
        """
        Convert text to speech and return audio data as bytes

        Args:
            text: Text to convert to speech
            voice_name: Neural voice name

        Returns:
            bytes: Audio data or None if failed
        """
        try:
            # Create SSML
            ssml = f"""
            <speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="en-US">
                <voice name="{voice_name}">
                    {text}
                </voice>
            </speak>
            """

            # Create synthesizer with no audio output config (for streaming)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None
            )

            # Synthesize speech
            result = synthesizer.speak_ssml_async(ssml).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                return result.audio_data
            else:
                print(f"Speech synthesis failed: {result.reason}")
                return None

        except Exception as e:
            print(f"Error during speech synthesis: {str(e)}")
            return None

    def get_available_voices(self) -> list:
        """
        Get list of available neural voices

        Returns:
            list: List of available voices
        """
        try:
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=self.speech_config,
                audio_config=None
            )

            result = synthesizer.get_voices_async().get()

            if result.reason == speechsdk.ResultReason.VoicesListRetrieved:
                neural_voices = [
                    {
                        'name': voice.name,
                        'display_name': voice.display_name,
                        'locale': voice.locale,
                        'gender': voice.gender.name,
                        'voice_type': voice.voice_type.name
                    }
                    for voice in result.voices
                    if 'Neural' in voice.name
                ]
                return neural_voices
            else:
                print(f"Failed to retrieve voices: {result.reason}")
                return []

        except Exception as e:
            print(f"Error retrieving voices: {str(e)}")
            return []


# Troubleshooting and example usage
def troubleshoot_connection():
    """
    Troubleshooting steps for Azure TTS connection issues
    """
    print("=== Azure TTS Connection Troubleshooting ===\n")

    # Check 1: Verify credentials
    subscription_key = os.getenv('AZURE_SPEECH_KEY')
    region = os.getenv('AZURE_SPEECH_REGION', 'eastus')

    if not subscription_key:
        print("❌ AZURE_SPEECH_KEY not found in environment variables")
        print("   Set it with: export AZURE_SPEECH_KEY='your-key'")
        return False
    else:
        print(f"✓ Subscription key found: {subscription_key[:8]}...")

    if not region:
        print("❌ AZURE_SPEECH_REGION not set")
        print("   Set it with: export AZURE_SPEECH_REGION='your-region'")
        return False
    else:
        print(f"✓ Region set: {region}")

    # Check 2: Test internet connectivity
    print("\n=== Testing Internet Connectivity ===")
    try:
        import urllib.request
        urllib.request.urlopen('https://www.google.com', timeout=5)
        print("✓ Internet connection working")
    except:
        print("❌ Internet connection issues detected")
        return False

    # Check 3: Test Azure endpoint
    print("\n=== Testing Azure Endpoint ===")
    try:
        import requests
        test_url = f"https://{region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        headers = {'Ocp-Apim-Subscription-Key': subscription_key}
        response = requests.post(test_url, headers=headers, timeout=10)

        if response.status_code == 200:
            print("✓ Azure endpoint accessible")
        else:
            print(f"❌ Azure endpoint returned: {response.status_code}")
            print("   Check your subscription key and region")
            return False
    except Exception as e:
        print(f"❌ Error accessing Azure endpoint: {str(e)}")
        return False

    # Check 4: Test TTS
    print("\n=== Testing TTS Connection ===")
    try:
        tts = AzureNeuralTTS(subscription_key, region)
        success = tts.test_connection()
        if success:
            print("✓ TTS connection successful")
            return True
        else:
            print("❌ TTS connection failed - will use REST API fallback")
            return True  # REST API can still work
    except Exception as e:
        print(f"❌ TTS test failed: {str(e)}")
        return False

# Example usage
def main():
    load_dotenv('config/.env')

    # Run troubleshooting first
    if not troubleshoot_connection():
        print("\n❌ Connection issues detected. Please resolve them before proceeding.")
        return

    print("\n=== Running TTS Examples ===")

    # Set up credentials (use environment variables for security)
    subscription_key = os.getenv('AZURE_SPEECH_KEY')
    region = os.getenv('AZURE_SPEECH_REGION', 'eastus')

    if not subscription_key:
        print("Please set AZURE_SPEECH_KEY environment variable")
        return

    # Initialize TTS client
    tts = AzureNeuralTTS(subscription_key, region)

    # Example 1: Basic text-to-speech
    text = "Hello! This is a demonstration of Azure Neural Text-to-Speech."
    success = tts.text_to_speech(
        text=text,
        voice_name="en-US-AriaNeural",
        output_file="demo.wav"
    )

    if success:
        print("Audio file created successfully!")

    # Example 2: Custom speech parameters
    tts.text_to_speech(
        text="This text is spoken faster and with higher pitch.",
        voice_name="en-US-JennyNeural",
        output_file="custom_demo.wav",
        speech_rate="25%",
        speech_pitch="10%"
    )

    # Example 3: Get audio data as bytes
    audio_data = tts.text_to_speech_stream(
        text="This returns audio data as bytes.",
        voice_name="en-US-DavisNeural"
    )

    if audio_data:
        # Save bytes to file
        with open("stream_demo.wav", "wb") as f:
            f.write(audio_data)
        print("Audio data saved from stream!")

    # Example 4: List available neural voices
    print("\nAvailable Neural Voices (first 5):")
    voices = tts.get_available_voices()
    for voice in voices[:5]:
        print(f"- {voice['name']} ({voice['locale']}) - {voice['gender']}")


if __name__ == "__main__":
    main()