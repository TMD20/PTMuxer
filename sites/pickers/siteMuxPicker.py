import sites.beyondHD.siteMuxData as beyondHD
import sites.blu.siteMuxData as blu
import sites.base.siteMuxData as base

def pickSite(site):
    if site==None:
        return base.MuxOBj()
    elif site.lower() == "beyondhd" or site.lower() == "bhd":
        return beyondHD.BeyondHD()

    elif site.lower() == "blu":
        return blu.Blu()
   
        
    
