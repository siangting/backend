from typing import List, Optional

import requests
from fastapi import APIRouter, HTTPException, Query

from ....schemas import NecessityPrice

router = APIRouter()


@router.get("/necessities-price", response_model=List[NecessityPrice])
def get_necessities_prices(
    category: Optional[str] = Query(None), commodity: Optional[str] = Query(None)
):
    response = requests.get(
        "https://opendata.ey.gov.tw/api/ConsumerProtection/NecessitiesPrice",
        params={"CategoryName": category, "Name": commodity},
    )
    response.raise_for_status()


    return response.json()
