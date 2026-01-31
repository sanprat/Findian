from thefuzz import process, fuzz
import logging
import sys
from sqlalchemy.orm import Session
from app.db.models import Stock

logger = logging.getLogger(__name__)

# Common Aliases (Moved from symbol_tokens.py)
SYMBOL_ALIASES = {
    "UBI": "UNIONBANK",
    "RIL": "RELIANCE",
    "SBI": "SBIN",
    "M&M": "M&M", 
    "TATAMOTORS": "TATAMOTORS",
    "LTIM": "LTIM",
    "ASHOKLEYLAND": "ASHOKLEY",
    "BAJFINANCE": "BAJFINANCE",
    "HDFCBANK": "HDFCBANK",
}

def static_resolve_alias(symbol: str) -> str:
    """Resolve common aliases to official NSE symbol"""
    # Remove spaces (e.g., "TATA STEEL" -> "TATASTEEL")
    clean_symbol = symbol.upper().replace(" ", "")
    return SYMBOL_ALIASES.get(clean_symbol, clean_symbol)

logger = logging.getLogger(__name__)

class SymbolLookup:
    def __init__(self, db: Session):
        self.db = db
        self._name_cache = {}  # { "Company Name": "SYMBOL" }
        self._load_cache()

    def _load_cache(self):
        """Load all stocks into memory for fast fuzzy matching."""
        try:
            stocks = self.db.query(Stock).filter(Stock.is_active == True).all()
            self._name_cache = {s.name: s.symbol for s in stocks}
            print(f"DEBUG: Loaded {len(self._name_cache)} stocks in cache.", file=sys.stdout) # To stdout
            logger.info(f"📚 Loaded {len(self._name_cache)} stocks for fuzzy lookup")
        except Exception as e:
            print(f"DEBUG: Cache FAIL: {e}", file=sys.stdout)
            logger.error(f"Failed to load lookup cache: {e}")

    def resolve(self, query: str) -> str:
        """
        Smart resolve a user query to a Stock Symbol.
        Flow:
        1. Normalize
        2. Static Alias (RIL -> RELIANCE)
        3. Exact Database Match (Symbol)
        4. Fuzzy Name Match
        """
        if not query:
            return None
            
        # 1. Normalize
        clean_query = query.upper().strip()
        
        # 2. Static Alias Lookup
        alias_result = static_resolve_alias(clean_query)
        
        # Initialize symbol set early (lazy load)
        if not hasattr(self, '_symbol_set'):
             if not self._name_cache:
                self._load_cache()
             self._symbol_set = set(self._name_cache.values())

        # CRITICAL FIX: Only accept alias if it resolves to a VALID symbol
        # (Prevent "Elecon Engineering" -> "ELECONENGINEERING" from returning early)
        if alias_result in self._symbol_set:
            return alias_result
            
        # 3. Exact Symbol Check (Original Query)
        if clean_query in self._symbol_set:
            return clean_query
            
        # 4. Fuzzy Name Match
        if not self._name_cache:
            self._load_cache()
            
        try:
            choices = list(self._name_cache.keys())
            
            # Use token_set_ratio for better partial/typo matching (e.g. "Elecon Engineerng" -> "Elecon Engineering Co Ltd")
            matches = process.extractOne(clean_query, choices, scorer=fuzz.token_set_ratio)
            if matches:
                match, score = matches
                print(f"DEBUG: '{clean_query}' vs '{match}' -> Score: {score}", file=sys.stderr, flush=True)
                
                if score >= 65:
                    symbol = self._name_cache[match]
                    return symbol
        except Exception as e:
            logger.error(f"Fuzzy lookup error: {e}")
            
        # Return original if no match found
        return clean_query

# Global singleton
_lookup_instance = None

def get_lookup_instance(db: Session):
    global _lookup_instance
    if _lookup_instance is None:
        _lookup_instance = SymbolLookup(db)
    return _lookup_instance

def resolve_symbol(db: Session, query: str) -> str:
    """
    Resolve symbol using cached lookup (Exact -> Fuzzy).
    """
    lookup = get_lookup_instance(db)
    return lookup.resolve(query)
