 
import queue
import itertools
import concurrent
import concurrent.futures
import traceback


import easyocr
from PIL import Image
import langcodes
from timeit import default_timer as timer

import tools.logger as logger
try:
    import tesserocr
except Exception as E:
    logger.print(E)
    logger.print(traceback.format_exc(),style="white")
    logger.print("Not using tesseocr")





NUM_THREADS = 4
ocr_queue = queue.Queue()



def perform_ocr(img):

    ocr_obj = ocr_queue.get(block=True, timeout=300)
    if isinstance(ocr_obj, easyocr.easyocr.Reader):
        try:
            return ocr_obj.readtext(img, detail=0)
         
        except queue.Empty:
            logger.logger.debug('Empty exception caught!')
            return None
        finally:
            if ocr_obj is not None:
                ocr_queue.put(ocr_obj)

    else:
        try:
            img = Image.open(img)
            ocr_obj.SetImage(img)
            return [ocr_obj.GetUTF8Text()]
        except queue.Empty:
                logger.logger.debug('Empty exception caught!')
                return None
        finally:
            if ocr_obj is not None:
                ocr_queue.put(ocr_obj)
    
 
 
def subocr(files,langcode):
        start_time = timer()
        for _ in range(NUM_THREADS):
            ocr_queue.put(getocr_obj(langcode)) 
        if ocr_queue.queue[0]==None:
            return ["Language Not Supported"]
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            res=executor.map(perform_ocr, files)
            
 
        output=[]
        for r in res:
            output.append(r)
        ocr_queue.queue.clear()
        elapsed = timer() - start_time
        logger.logger.info(f"Execution Time {elapsed } seconds")
        return list(itertools.chain.from_iterable(output))
def getocr_obj(langcode):
    if langcode in easyocr.config.all_lang_list:
         return easyocr.Reader([langcode],gpu=False)
    logger.logger.warning(f"easyocr does not support {str(langcodes.get(langcode).display_name())}\nTrying tesseract-ocr")
    try:
        return tesserocr.PyTessBaseAPI( lang=langcodes.Language.get(langcode).to_alpha3())
    except Exception as E:
        logger.logger.warning(f"tesseract-ocr ran into an issue")
        logger.logger.debug(str(E))
        logger.logger.debug(traceback.format_exc()) 
