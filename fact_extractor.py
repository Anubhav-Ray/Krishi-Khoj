"""
Rule-based fact extraction engine for Krishi Khoj.
Extracts structured farming facts from text using pattern matching.

IMPORTANT: This module only EXTRACTS existing facts from documents.
It does NOT generate or create new farming advice.

Categories:
    - Fertilizer: Nutrient doses, application schedules, NPK ratios
    - Seed: Varieties, seed rates, treatment
    - Irrigation: Watering schedules, water requirements
    - Pest: Pest/disease management, pesticide doses
    - Soil: Soil types, pH requirements, preparation
    - Yield: Expected yields, production data
    - Season: Sowing/harvesting times, crop calendars
    - General: Other farming facts
"""
import re
from typing import List, Dict, Optional, Tuple


# ===== CROP DICTIONARY =====
CROP_NAMES = [
    # Cereals
    'wheat', 'rice', 'paddy', 'maize', 'corn', 'bajra', 'pearl millet',
    'jowar', 'sorghum', 'ragi', 'finger millet', 'barley',
    # Pulses
    'moong', 'mung bean', 'urad', 'black gram', 'arhar', 'pigeon pea',
    'tur', 'chana', 'chickpea', 'gram', 'masoor', 'lentil', 'pea',
    # Oilseeds
    'mustard', 'rapeseed', 'groundnut', 'peanut', 'soybean', 'sunflower',
    'sesame', 'til', 'linseed',
    # Cash crops
    'sugarcane', 'cotton', 'jute', 'tobacco', 'tea', 'coffee', 'rubber',
    # Vegetables
    'potato', 'tomato', 'onion', 'brinjal', 'eggplant', 'cauliflower',
    'cabbage', 'carrot', 'radish', 'spinach', 'palak', 'okra', 'bhindi',
    'pumpkin', 'cucumber', 'bottle gourd', 'bitter gourd',
    # Fruits
    'mango', 'banana', 'guava', 'papaya', 'citrus', 'orange', 'grape',
    'apple', 'pomegranate', 'litchi', 'watermelon',
    # Spices
    'turmeric', 'ginger', 'chilli', 'pepper', 'cumin', 'coriander',
    'cardamom', 'clove', 'fennel',
]

# ===== SEASON KEYWORDS =====
SEASON_KEYWORDS = {
    'kharif': 'Kharif',
    'rabi': 'Rabi',
    'zaid': 'Zaid',
    'summer': 'Zaid',
    'monsoon': 'Kharif',
    'winter': 'Rabi',
    'spring': 'Zaid',
}

# ===== REGION PATTERNS =====
REGION_NAMES = [
    'punjab', 'haryana', 'uttar pradesh', 'up', 'madhya pradesh', 'mp',
    'rajasthan', 'gujarat', 'maharashtra', 'karnataka', 'tamil nadu',
    'andhra pradesh', 'telangana', 'kerala', 'west bengal', 'bihar',
    'odisha', 'assam', 'jharkhand', 'chhattisgarh', 'uttarakhand',
    'himachal pradesh', 'jammu', 'kashmir', 'north india', 'south india',
    'east india', 'west india', 'central india', 'indo-gangetic',
    'deccan', 'coastal', 'north-east', 'northeast',
]

# ===== CATEGORY PATTERNS =====
# Each pattern: (compiled_regex, category_name)

CATEGORY_PATTERNS = {
    'Fertilizer': [
        r'\b(?:fertiliz|manure|nutrient|nitrogen|phosph|potash|potassium|npk|n[:\s]*p[:\s]*k|urea|dap|mop|superphosphate|ammonium|sulphate|zinc sulphate|borax|micronutrient|fym|farm\s*yard|compost|vermicompost|bio.?fertiliz|azotobacter|rhizobium|top.?dress|basal\s*dose|split\s*(?:dose|application))\b',
        r'\b\d+[\s-]*(?:kg|g|ml|litre|l|ton|tonne|quintal|q)[\s/]*(?:ha|hectare|acre|bigha)\b.*\b(?:appl|dose|spread|broadcast|mix)\b',
        r'\b(?:appl|dose|spread|broadcast)\b.*\b\d+[\s-]*(?:kg|g|ml)[\s/]*(?:ha|hectare|acre)\b',
    ],
    'Seed': [
        r'\b(?:seed\s*rate|seeding\s*rate|seed\s*treatment|seed\s*dressing|variet(?:y|ies)|cultivar|hybrid|improved\s*(?:seed|variet)|recommended\s*variet|certified\s*seed|foundation\s*seed|breeder\s*seed|seed\s*(?:drill|spacing|depth|germination|viability|inoculation))\b',
        r'\b(?:sow(?:ing|n)?|plant(?:ing|ed)?)\b.*\b(?:spacing|distance|apart|row|cm|inch)\b',
    ],
    'Irrigation': [
        r'\b(?:irrigat|water(?:ing|ed)?|moisture|drought|rain.?fed|canal|drip|sprinkler|flood\s*irrigat|furrow|border\s*strip|check\s*basin|critical\s*(?:stage|period)|cwsi|water\s*requirement|water\s*use|et\s*crop|evapotranspiration)\b',
        r'\b(?:das|dap|days?\s*after\s*(?:sowing|planting|transplanting))\b.*\b(?:irrigat|water)\b',
    ],
    'Pest': [
        r'\b(?:pest|insect|disease|fungus|fungi|blight|rust|smut|wilt|rot|mildew|mosaic|virus|borer|aphid|jassid|whitefly|thrip|mite|caterpillar|armyworm|bollworm|shoot\s*fly|stem\s*borer|leaf\s*folder|hopper|weevil|termite|nematode|weed|herbicid|insecticid|fungicid|pesticid|spray|dust(?:ing)?|ipm|integrated\s*pest|biological\s*control|trap\s*crop|neem\s*oil|bt\s*cotton)\b',
        r'\b(?:spray|appl|treat|drench|dust)\b.*\b(?:g|ml|l|kg)[\s/]*(?:litre|l|ha|hectare|acre)\b.*\b(?:contro|manage|prevent|protect)\b',
    ],
    'Soil': [
        r'\b(?:soil\s*(?:type|test|health|preparation|fertility|conservation|erosion|moisture|structure|texture|organic|carbon|salinity|alkalinity|acidity|amendment|reclamation|mulch)|ph\s*(?:level|range|value|\d)|loam|sandy|clay|silt|alluvial|laterite|black\s*(?:soil|cotton)|red\s*soil|land\s*preparation|plough|harrow|levell?ing|tilth|tillage|zero\s*till|conservation\s*(?:agriculture|tillage))\b',
    ],
    'Yield': [
        r'\b(?:yield|production|productivity|harvest(?:ed|ing)?|output|quintal|tonne|ton|q[\s/]*(?:ha|hectare|acre)|(?:kg|tonne|ton)[\s/]*(?:ha|hectare|acre))\b.*\b(?:expect|average|potential|maximum|minimum|total|per\s*(?:ha|hectare|acre)|estimated)\b',
        r'\b(?:expect|average|potential)\b.*\b(?:yield|production|productivity)\b',
        r'\b\d+[\s-]*(?:to|-)\s*\d+\s*(?:q|quintal|tonne|ton|kg)[\s/]*(?:ha|hectare|acre)\b',
    ],
    'Season': [
        r'\b(?:sowing\s*(?:time|date|period|window|season)|planting\s*(?:time|date|period)|harvest(?:ing)?\s*(?:time|date|period|season)|crop\s*(?:duration|season|calendar|cycle|rotation)|kharif|rabi|zaid|(?:june|july|august|september|october|november|december|january|february|march|april|may)\s*(?:to|-)\s*(?:june|july|august|september|october|november|december|january|february|march|april|may))\b',
        r'\b(?:transplant(?:ing|ed)?|nursery)\b.*\b(?:month|week|date|time|period)\b',
    ],
}

# Compile all patterns
COMPILED_PATTERNS = {}
for category, patterns in CATEGORY_PATTERNS.items():
    COMPILED_PATTERNS[category] = [re.compile(p, re.IGNORECASE) for p in patterns]


# ===== VALUE/UNIT EXTRACTION =====
VALUE_UNIT_PATTERN = re.compile(
    r'(\d+(?:\.\d+)?)\s*(?:to|-)\s*(\d+(?:\.\d+)?)\s*(kg|g|ml|l|litre|litres|q|quintal|quintals|tonne|tonnes|ton|tons|mm|cm|m|ha|hectare|acre|%|ppm|days?|weeks?|months?|hours?)'
    r'|(\d+(?:\.\d+)?)\s*(kg|g|ml|l|litre|litres|q|quintal|quintals|tonne|tonnes|ton|tons|mm|cm|m|ha|hectare|acre|%|ppm|days?|weeks?|months?|hours?)',
    re.IGNORECASE
)


def extract_value_unit(text: str) -> Tuple[Optional[float], Optional[str]]:
    """Extract the first numeric value and its unit from text."""
    match = VALUE_UNIT_PATTERN.search(text)
    if match:
        if match.group(1) and match.group(2):
            # Range: take average
            val = (float(match.group(1)) + float(match.group(2))) / 2
            unit = match.group(3).lower()
        elif match.group(4):
            val = float(match.group(4))
            unit = match.group(5).lower()
        else:
            return None, None

        # Normalize units
        unit_map = {
            'l': 'litre', 'litres': 'litre',
            'q': 'quintal', 'quintals': 'quintal',
            'tonnes': 'tonne', 'tons': 'tonne', 'ton': 'tonne',
            'days': 'days', 'day': 'days',
            'weeks': 'weeks', 'week': 'weeks',
            'months': 'months', 'month': 'months',
            'hours': 'hours', 'hour': 'hours',
        }
        unit = unit_map.get(unit, unit)
        return val, unit
    return None, None


def detect_crop(text: str) -> Optional[str]:
    """Detect crop name mentioned in the text."""
    text_lower = text.lower()
    for crop in CROP_NAMES:
        # Word boundary matching
        if re.search(r'\b' + re.escape(crop) + r'\b', text_lower):
            return crop.title()
    return None


def detect_season(text: str) -> Optional[str]:
    """Detect cropping season mentioned in text."""
    text_lower = text.lower()
    for keyword, season in SEASON_KEYWORDS.items():
        if keyword in text_lower:
            return season
    return None


def detect_region(text: str) -> Optional[str]:
    """Detect geographic region mentioned in text."""
    text_lower = text.lower()
    for region in REGION_NAMES:
        if re.search(r'\b' + re.escape(region) + r'\b', text_lower):
            return region.title()
    return None


def classify_sentence(sentence: str) -> Optional[str]:
    """Classify a sentence into a fact category, or None if not a fact."""
    for category, patterns in COMPILED_PATTERNS.items():
        for pattern in patterns:
            if pattern.search(sentence):
                return category
    return None


def split_into_sentences(text: str) -> List[str]:
    """Split text into sentences, handling common abbreviations."""
    # Protect common abbreviations
    text = re.sub(r'\b(Dr|Mr|Mrs|Ms|Prof|Sr|Jr|etc|vs|viz|approx|ca|i\.e|e\.g)\.',
                  r'\1<DOT>', text)
    # Protect decimal numbers
    text = re.sub(r'(\d)\.(\d)', r'\1<DECIMAL>\2', text)

    # Split on sentence boundaries
    sentences = re.split(r'[.!?]\s+|\n+', text)

    # Restore protected dots
    result = []
    for s in sentences:
        s = s.replace('<DOT>', '.').replace('<DECIMAL>', '.').strip()
        # Filter out very short or non-informative sentences
        if len(s) > 20 and any(c.isalpha() for c in s):
            result.append(s)
    return result


def extract_facts_from_text(text: str, page_number: int,
                            document_crop: str = None) -> List[Dict]:
    """
    Extract structured facts from a page of text.

    Args:
        text: Raw text from a PDF page
        page_number: Page number (1-indexed)
        document_crop: Default crop name if detected at document level

    Returns:
        List of fact dictionaries with fields:
        - crop_name, category, fact_text, value, unit,
          season, region, page_number, original_text
    """
    facts = []
    sentences = split_into_sentences(text)

    for sentence in sentences:
        category = classify_sentence(sentence)
        if category is None:
            continue

        # Extract structured fields
        crop = detect_crop(sentence) or document_crop
        season = detect_season(sentence)
        region = detect_region(sentence)
        value, unit = extract_value_unit(sentence)

        # Clean the fact text
        fact_text = sentence.strip()
        if len(fact_text) > 500:
            fact_text = fact_text[:497] + '...'

        fact = {
            'crop_name': crop,
            'category': category,
            'fact_text': fact_text,
            'value': value,
            'unit': unit,
            'season': season,
            'region': region,
            'page_number': page_number,
            'original_text': sentence.strip()
        }
        facts.append(fact)

    return facts


def extract_facts_from_document(pages: List[Dict]) -> List[Dict]:
    """
    Extract facts from all pages of a document.

    Args:
        pages: List of {'page_number': int, 'text': str} from PDFProcessor

    Returns:
        List of all extracted facts across all pages
    """
    all_facts = []

    # First pass: detect the primary crop of the document
    full_text = ' '.join(p['text'] for p in pages[:3])  # Check first 3 pages
    document_crop = detect_crop(full_text)

    # Second pass: extract facts page by page
    for page in pages:
        page_facts = extract_facts_from_text(
            page['text'],
            page['page_number'],
            document_crop
        )
        all_facts.extend(page_facts)

    return all_facts


def get_extraction_summary(facts: List[Dict]) -> Dict:
    """Generate a summary of extracted facts."""
    categories = {}
    crops = set()
    seasons = set()
    regions = set()

    for fact in facts:
        cat = fact['category']
        categories[cat] = categories.get(cat, 0) + 1
        if fact.get('crop_name'):
            crops.add(fact['crop_name'])
        if fact.get('season'):
            seasons.add(fact['season'])
        if fact.get('region'):
            regions.add(fact['region'])

    return {
        'total_facts': len(facts),
        'by_category': categories,
        'crops_found': sorted(crops),
        'seasons_found': sorted(seasons),
        'regions_found': sorted(regions)
    }
