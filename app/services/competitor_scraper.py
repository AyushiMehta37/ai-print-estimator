"""
Competitor pricing scraper for print services.
Provides competitive pricing data for comparison.
"""

import asyncio
import json
import re
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup


class CompetitorScraper:
    """
    Scrapes competitor pricing for print services.
    Currently supports major Indian print service providers.
    """

    COMPETITORS = {
        "PhotoPrint Pro": {
            "url": "https://www.photoprintpro.com",
            "selectors": {
                "price": ".price, .cost, [data-price]",
                "business_cards": ".business-cards, .visiting-cards",
                "posters": ".posters, .banners"
            }
        },
        "PosterExpress": {
            "url": "https://www.posterexpress.in",
            "selectors": {
                "price": ".product-price, .price-value",
                "business_cards": ".business-cards",
                "posters": ".posters"
            }
        },
        "PrintHub": {
            "url": "https://www.printhub.com",
            "selectors": {
                "price": ".pricing, .rate",
                "business_cards": ".cards",
                "posters": ".large-format"
            }
        }
    }

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.client = httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            }
        )

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.client.aclose()

    async def get_competitor_prices(
        self,
        product_type: str,
        quantity: int,
        size: str = None
    ) -> List[Dict]:
        """
        Get competitor pricing for a specific product.

        Args:
            product_type: Type of print product (business_cards, posters, etc.)
            quantity: Print quantity
            size: Size specification (optional)

        Returns:
            List of competitor price data
        """
        tasks = []
        for name, config in self.COMPETITORS.items():
            tasks.append(self._scrape_competitor(name, config, product_type, quantity, size))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Filter out exceptions and None results
        valid_results = []
        for result in results:
            if isinstance(result, dict) and result.get('price'):
                valid_results.append(result)

        return valid_results

    async def _scrape_competitor(
        self,
        name: str,
        config: Dict,
        product_type: str,
        quantity: int,
        size: Optional[str]
    ) -> Optional[Dict]:
        """
        Scrape pricing from a specific competitor.
        """
        try:
            # Construct search URL
            search_url = self._build_search_url(config['url'], product_type, quantity, size)

            response = await self.client.get(search_url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, 'html.parser')

            # Try to find pricing information
            price = self._extract_price(soup, config['selectors'])

            if price:
                return {
                    'name': name,
                    'price': price,
                    'url': search_url,
                    'quantity': quantity,
                    'product_type': product_type
                }

        except Exception as e:
            # Log error but don't fail completely
            print(f"Error scraping {name}: {e}")

        return None

    def _build_search_url(self, base_url: str, product_type: str, quantity: int, size: str = None) -> str:
        """
        Build search URL for competitor site.
        """
        # Simple URL construction - in production, this would be more sophisticated
        product_map = {
            'business_cards': 'business-cards',
            'posters': 'posters',
            'brochures': 'brochures',
            'flyers': 'flyers'
        }

        product_slug = product_map.get(product_type, product_type)

        if 'photoprintpro' in base_url:
            return f"{base_url}/products/{product_slug}?qty={quantity}"
        elif 'posterexpress' in base_url:
            return f"{base_url}/print/{product_slug}/{quantity}"
        else:
            return f"{base_url}/search?q={product_slug}+{quantity}"

    def _extract_price(self, soup: BeautifulSoup, selectors: Dict) -> Optional[float]:
        """
        Extract price from HTML using various selectors.
        """
        # Try different price selectors
        price_selectors = [
            selectors.get('price', ''),
            '.price', '.cost', '[data-price]',
            '.product-price', '.rate', '.pricing'
        ]

        for selector in price_selectors:
            if not selector:
                continue

            elements = soup.select(selector)
            for element in elements:
                text = element.get_text().strip()
                price = self._parse_price_text(text)
                if price:
                    return price

        # Try regex on all text
        all_text = soup.get_text()
        return self._parse_price_text(all_text)

    def _parse_price_text(self, text: str) -> Optional[float]:
        """
        Parse price from text using regex.
        Handles various formats: ₹500, Rs. 500, 500 INR, etc.
        """
        # Common Indian price patterns
        patterns = [
            r'₹\s*(\d+(?:,\d+)*(?:\.\d{2})?)',  # ₹500.00
            r'Rs\.?\s*(\d+(?:,\d+)*(?:\.\d{2})?)',  # Rs. 500
            r'INR\s*(\d+(?:,\d+)*(?:\.\d{2})?)',  # INR 500
            r'(\d+(?:,\d+)*(?:\.\d{2})?)\s*INR',  # 500 INR
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                try:
                    # Remove commas and convert to float
                    price = float(match.replace(',', ''))
                    if 10 <= price <= 50000:  # Reasonable price range
                        return price
                except ValueError:
                    continue

        return None

    async def get_average_competitor_price(
        self,
        product_type: str,
        quantity: int,
        size: str = None
    ) -> Optional[float]:
        """
        Get average competitor price for comparison.
        """
        competitors = await self.get_competitor_prices(product_type, quantity, size)

        if not competitors:
            return None

        prices = [c['price'] for c in competitors]
        return sum(prices) / len(prices)


# Mock data for development/testing
MOCK_COMPETITOR_DATA = [
    {"name": "PhotoPrint Pro", "price": 3200.0},
    {"name": "PosterExpress", "price": 2950.0},
    {"name": "PrintHub", "price": 2800.0}
]


async def get_competitor_prices_mock(
    product_type: str,
    quantity: int,
    size: str = None
) -> List[Dict]:
    """
    Mock competitor pricing for development.
    """
    # Simulate API delay
    await asyncio.sleep(0.5)
    return MOCK_COMPETITOR_DATA


if __name__ == "__main__":
    # Test the scraper
    async def test():
        async with CompetitorScraper() as scraper:
            prices = await scraper.get_competitor_prices("business_cards", 100)
            print("Competitor prices:", json.dumps(prices, indent=2))

    asyncio.run(test())