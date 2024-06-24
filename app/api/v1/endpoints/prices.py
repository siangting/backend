from fastapi import APIRouter, HTTPException, Query
import requests
from typing import List, Optional
from ....schemas import NecessityPrice

router = APIRouter()

@router.get("/necessities-price", response_model=List[NecessityPrice])
def get_necessities_prices(category: Optional[str] = Query(None), commodity: Optional[str] = Query(None)):
    try:
        response = requests.get(
            "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
            params={"CategoryName": category, "Name": commodity}
        )
        response.raise_for_status()
    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=str(e))

    return response.json()
