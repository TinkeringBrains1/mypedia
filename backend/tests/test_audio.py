import subprocess
import unittest
from unittest.mock import patch

from app.services.audio import AudioConversionError, convert_for_gemini


class AudioConversionTest(unittest.TestCase):
    @patch("app.services.audio.shutil.which", return_value="ffmpeg")
    @patch("app.services.audio.subprocess.run")
    def test_webm_is_converted_to_gemini_supported_wav(self, run, _which) -> None:
        def create_wav(command, **_kwargs):
            output_path = command[-1]
            with open(output_path, "wb") as output:
                output.write(b"RIFF wav")
            return subprocess.CompletedProcess(command, 0)

        run.side_effect = create_wav
        converted, mime_type = convert_for_gemini(b"webm-data", "audio/webm")

        self.assertEqual(converted, b"RIFF wav")
        self.assertEqual(mime_type, "audio/wav")
        self.assertIn("pcm_s16le", run.call_args.args[0])

    @patch("app.services.audio._find_ffmpeg", return_value=None)
    def test_missing_ffmpeg_returns_a_clear_error(self, _find_ffmpeg) -> None:
        with self.assertRaises(AudioConversionError):
            convert_for_gemini(b"webm-data", "audio/webm")
