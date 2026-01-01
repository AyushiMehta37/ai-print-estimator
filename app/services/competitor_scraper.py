import asyncio
import re
from typing import List, Dict, Optional

import httpx
from bs4 import BeautifulSoup


class CompetitorScraper:
    COMPETITORS = {
        "PhotoPrint Pro": {
            "url": "https://www.photoprintpro.com",
            "selectors": [".price", ".cost", "[data-price]"]
        },
        "PosterExpress": {
            "url": "https://www.posterexpress.in",
            "selectors": [".product-price", ".price-value"]
        },
        "PrintHub": {
            "url": "https://www.printhub.com",
            "selectors": [".pricing", ".rate"]
        }
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_competitor_prices(self, product_type: str, quantity: int, size: str = None) -> List[Dict]:
        tasks = [self._scrape_competitor(name, config, product_type, quantity, size) for name, config in self.COMPETITORS.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return [r for r in results if isinstance(r, dict) and r.get('price')]

    async def _scrape_competitor(self, name: str, config: Dict, product_type: str, quantity: int, size: Optional[str]) -> Optional[Dict]:
        try:
            search_url = self._build_search_url(config['url'], product_type, quantity, size)
            response = await self.client.get(search_url)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            price = self._extract_price(soup, config['selectors'])
            if price:
                return {'name': name, 'price': price, 'url': search_url, 'quantity': quantity, 'product_type': product_type}
        except Exception:
            pass
        return None

    def _build_search_url(self, base_url: str, product_type: str, quantity: int, size: str = None) -> str:
        product_map = {'business_cards': 'business-cards', 'posters': 'posters', 'brochures': 'brochures', 'flyers': 'flyers'}
        product_slug = product_map.get(product_type, product_type)
        if 'photoprintpro' in base_url:
            return f"{base_url}/products/{product_slug}?qty={quantity}"
        elif 'posterexpress' in base_url:
            return f"{base_url}/print/{product_slug}/{quantity}"
        return f"{base_url}/search?q={product_slug}+{quantity}"

    def _extract_price(self, soup: BeautifulSoup, selectors: List[str]) -> Optional[float]:
        all_selectors = selectors + ['.price', '.cost', '[data-price]', '.product-price', '.rate', '.pricing']
        for selector in all_selectors:
            elements = soup.select(selector)
            for element in elements:
                price = self._parse_price_text(element.get_text().strip())
                if price:
                    return price
        return self._parse_price_text(soup.get_text())

    def _parse_price_text(self, text: str) -> Optional[float]:
        patterns = [
            r'₹\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
            r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
            r'INR\s*(\d+(?:,\d+)*(?:\.\d{2})?)',
            r'(\d+(?:,\d+)*(?:\.\d{2})?)\s*INR'
        ]
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    price = float(match.replace(',', ''))
                    if 10 <= price <= 50000:
                        return price
                except ValueError:
                    continue
        return None


MOCK_COMPETITOR_DATA = [
    {"name": "PhotoPrint Pro", "price": 3200.0},
    {"name": "PosterExpress", "price": 2950.0},
    {"name": "PrintHub", "price": 2800.0}
]


async def get_competitor_prices_mock(product_type: str, quantity: int, size: str = None) -> List[Dict]:
    await asyncio.sleep(0.5)
    return MOCK_COMPETITOR_DATA