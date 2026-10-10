from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List, Union
import requests
from llm_workflows.structured_template import get_structured_business_plan_student, get_structured_business_plan_mentor
import os
import logging
import tempfile
from urllib.parse import urlparse
from utils.full_multi_updated2 import convert_pdf_to_images, IMAGE_DPI, OUTPUT_DIR
class PayloadItem(BaseModel):
    url: str
    type: str


def validate_url(url: str) -> str:
    """Accept only http(s) URLs. Local paths and other schemes (file://, ftp://) are rejected."""
    parsed = urlparse(url or "")
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise HTTPException(status_code=400, detail="url must be an absolute http(s) URL")
    return url


def download_to_temp(url: str, suffix: str) -> str:
    """Download `url` into a temporary file and return its path (caller deletes it)."""
    validate_url(url)
    try:
        response = requests.get(url, timeout=60)
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Failed to download file: {e}")
    if response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to download file from link.")
    fd, path = tempfile.mkstemp(suffix=suffix)
    with os.fdopen(fd, "wb") as f:
        f.write(response.content)
    return path


router = APIRouter()


@router.post("/process-pdf")
def process_pdf_api(payload: Union[PayloadItem, List[PayloadItem]]):
    # Expect payload as [{url: '', type: ''}]
    import json
    try:
        # Accept either a list of PayloadItem or a single PayloadItem
        if isinstance(payload, list) and payload:
            item = payload[0]
        else:
            item = payload
        url = item.url
        file_type = item.type
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Invalid payload: {e}")

    if file_type == 'pdf' and url:
        import concurrent.futures
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        pdf_to_use = download_to_temp(url, ".pdf")
        try:
            image_files = convert_pdf_to_images(pdf_to_use, OUTPUT_DIR, IMAGE_DPI)
            all_pages_data = []
            # Parallel OCR processing using process_single_page
            from utils.full_multi_updated2 import process_single_page, save_results, MAX_WORKERS
            with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                future_to_page = {
                    executor.submit(process_single_page, image_path, i + 1): i + 1
                    for i, image_path in enumerate(image_files)
                }
                for future in concurrent.futures.as_completed(future_to_page):
                    page_num = future_to_page[future]
                    try:
                        page_data = future.result()
                        all_pages_data.append(page_data)
                    except Exception as exc:
                        logging.error(f'Page {page_num} generated an exception: {exc}')
            # Sort results by page_number
            all_pages_data.sort(key=lambda p: p.get('page_number', 0))
            # Save results (optional, can be commented out)
            # save_results(all_pages_data, OUTPUT_DIR, "api_result")
            student_structured = get_structured_business_plan_student(all_pages_data)
            mentor_structured = get_structured_business_plan_mentor(all_pages_data)
            return {
                "transcribe": json.dumps(all_pages_data, ensure_ascii=False),
                "structured_data_student": student_structured,
                "structured_data_mentor": mentor_structured
            }
        except Exception as e:
            logging.error(f"API error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            if os.path.exists(pdf_to_use):
                os.remove(pdf_to_use)
    elif file_type == 'audio' and url:
        try:
            from llm_workflows.audio_text import generate_subtitles
            audio_path = download_to_temp(url, os.path.splitext(urlparse(url).path)[1] or ".m4a")
            try:
                # generate_subtitles returns (original_srt, multiline_srt, transcript, language)
                _, _, transcript, _ = generate_subtitles(audio_path)
            finally:
                os.remove(audio_path)
            if not transcript:
                raise HTTPException(status_code=500, detail="Transcription failed (is FFmpeg installed?)")
            # Apply get_structured_business_plan to transcript as a single page
            pages_data = [{"full_text": transcript}]
            student_structured = get_structured_business_plan_student(pages_data)
            mentor_structured = get_structured_business_plan_mentor(pages_data)
            return {
                "transcribe": transcript,
                "structured_data_student": student_structured,
                "structured_data_mentor": mentor_structured
            }
        except HTTPException:
            raise
        except Exception as e:
            logging.error(f"Audio API error: {e}")
            raise HTTPException(status_code=500, detail=str(e))
    else:
        try:
            summary_path = os.path.join(os.path.dirname(__file__), '..', 'transcription_summary_20250927_194111.json')
            with open(summary_path, 'r', encoding='utf-8') as f:
                summary = json.load(f)
            status = summary.get('results', [{}])[0].get('status', '')
            # Apply get_structured_business_plan to status as a single page
            pages_data = [{"full_text": status}]
            student_structured = get_structured_business_plan_student(pages_data)
            mentor_structured = get_structured_business_plan_mentor(pages_data)
            return {
                "transcribe": status,
                "structured_data_student": student_structured,
                "structured_data_mentor": mentor_structured
            }
        except Exception as e:
            logging.error(f"Fallback error: {e}")
            raise HTTPException(status_code=500, detail=f"Fallback error: {e}")
