from Foundation import NSURL
from Vision import (
    VNImageRequestHandler, VNRecognizeTextRequest,
    VNRequestTextRecognitionLevelAccurate,  # enum value == 0
    VNRecognizeTextRequestRevision3          # or 4 if your OS supports
)
from Quartz import CGImageSourceCreateWithURL, CGImageSourceCreateImageAtIndex

def run_ocr(path: str) -> str:
    url = NSURL.fileURLWithPath_(path)
    src = CGImageSourceCreateWithURL(url, None)
    cgimg = CGImageSourceCreateImageAtIndex(src, 0, None)
    req = VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["ko-KR"])    # locale, not just "ko"
    req.setUsesLanguageCorrection_(True)
    try:
        req.setRevision_(VNRecognizeTextRequestRevision3)
    except Exception:
        pass
    req.setMinimumTextHeight_(0.02)

    handler = VNImageRequestHandler.alloc().initWithCGImage_options_(cgimg, None)
    ok = handler.performRequests_error_([req], None)
    if not ok:
        return ""

    lines = []
    for obs in (req.results() or []):
        cand = obs.topCandidates_(1)
        if cand and len(cand) > 0:
            lines.append(cand[0].string())
    return "\n".join(lines)

if __name__ == "__main__":
    print(run_ocr("/Users/slimslavik/core/back-end/ridi_images/page_0005.png"))
