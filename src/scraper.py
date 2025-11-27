"""
Crossword puzzle scraper with multiple data sources

IMPORTANT: This scraper includes multiple strategies:
1. Synthetic data generation (for testing and demonstration)
2. Public crossword archives (where permitted)
3. User-uploaded puzzles

Always respect website terms of service and robots.txt
"""
import json
import time
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging
from tqdm import tqdm

import requests
from bs4 import BeautifulSoup

from utils import (
    load_config,
    save_jsonl,
    format_date_as_puzzle_id,
    get_day_of_week,
    validate_puzzle_structure,
    check_rotational_symmetry,
    number_grid,
    extract_words_from_grid
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SyntheticPuzzleGenerator:
    """
    Generates realistic synthetic crossword puzzles for training data
    Uses real English words and themed answers
    """

    def __init__(self):
        # Load comprehensive word lists
        self.all_words = self._load_word_list()

        # Organize words by length for efficient lookup
        self.words_by_length = {}
        for word in self.all_words:
            length = len(word)
            if length not in self.words_by_length:
                self.words_by_length[length] = []
            self.words_by_length[length].append(word)

        # Organize by difficulty
        self.word_pools = self._organize_by_difficulty()

        # Theme definitions with associated words
        self.themes = {
            "Space": ["APOLLO", "ORBIT", "SATELLITE", "ASTRONAUT", "GALAXY", "NEBULA", "COMET", "METEOR", "PLANET", "ROCKET", "LUNAR", "SOLAR", "COSMOS", "ECLIPSE", "CRATER"],
            "Movies": ["ACTOR", "CINEMA", "DIRECTOR", "SCREENPLAY", "DRAMA", "COMEDY", "THRILLER", "OSCARS", "STUDIO", "PREMIERE", "TICKET", "POPCORN", "SCENE", "CAST", "FILM"],
            "Sports": ["BASEBALL", "TENNIS", "MARATHON", "STADIUM", "SOCCER", "HOCKEY", "ATHLETE", "OLYMPICS", "COACH", "VICTORY", "TROPHY", "PITCH", "GOAL", "SCORE", "TEAM"],
            "Music": ["PIANO", "GUITAR", "VIOLIN", "MELODY", "HARMONY", "RHYTHM", "CONCERT", "SYMPHONY", "OPERA", "JAZZ", "BLUES", "TEMPO", "CHORD", "SCALE", "NOTE"],
            "Food": ["RECIPE", "FLAVOR", "SPICE", "CUISINE", "CHEF", "KITCHEN", "BAKING", "PASTA", "SALAD", "DESSERT", "SAUCE", "GRILL", "TASTE", "DISH", "MEAL"],
            "Science": ["ATOM", "MOLECULE", "THEORY", "EXPERIMENT", "LABORATORY", "PHYSICS", "CHEMISTRY", "BIOLOGY", "RESEARCH", "HYPOTHESIS", "DATA", "CELL", "GENE", "ENERGY", "FORCE"],
            "Ocean": ["WAVE", "TIDE", "CORAL", "SHARK", "WHALE", "DOLPHIN", "OCEAN", "MARINE", "REEF", "SHELL", "BEACH", "COAST", "DEEP", "SURF", "SALT"],
            "Nature": ["FOREST", "MOUNTAIN", "RIVER", "TREE", "FLOWER", "BIRD", "ANIMAL", "PLANT", "LEAF", "RAIN", "CLOUD", "WIND", "SOIL", "SEED", "BLOOM"],
            "Travel": ["AIRPORT", "FLIGHT", "HOTEL", "PASSPORT", "VOYAGE", "JOURNEY", "TOURIST", "LUGGAGE", "TICKET", "BEACH", "RESORT", "CRUISE", "TRIP", "VISIT", "EXPLORE"],
            "Books": ["NOVEL", "AUTHOR", "LIBRARY", "CHAPTER", "PAGE", "STORY", "FICTION", "POETRY", "WRITER", "READER", "PLOT", "TITLE", "GENRE", "PROSE", "VERSE"],
            "Technology": ["COMPUTER", "INTERNET", "SOFTWARE", "DIGITAL", "ROBOT", "KEYBOARD", "SCREEN", "MOUSE", "NETWORK", "SERVER", "CODING", "EMAIL", "BYTE", "DATA", "APPS"],
            "History": ["ANCIENT", "EMPIRE", "BATTLE", "CENTURY", "ARTIFACT", "DYNASTY", "EXPLORER", "MONUMENT", "TREATY", "COLONIAL", "MEDIEVAL", "REIGN", "ERA", "RELIC", "ARCHIVE"]
        }

    def _load_word_list(self) -> List[str]:
        """Load comprehensive English word list"""
        words = set()

        # Try to load from system dictionary
        try:
            with open('/usr/share/dict/words', 'r') as f:
                for line in f:
                    word = line.strip().upper()
                    # Filter for crossword-appropriate words
                    if 3 <= len(word) <= 15 and word.isalpha():
                        words.add(word)
        except FileNotFoundError:
            logger.warning("System dictionary not found, using built-in word list")

        # Add comprehensive built-in word list
        words.update(self._get_comprehensive_word_list())

        return sorted(list(words))

    def _get_comprehensive_word_list(self) -> List[str]:
        """Comprehensive built-in word list for crosswords"""
        return [
            # Common 3-letter words
            "ACE", "ACT", "ADD", "AGE", "AID", "AIM", "AIR", "ALL", "AND", "ANT", "ANY", "APE", "ARC", "ARE", "ARK", "ARM", "ART", "ASH", "ASK", "ATE",
            "BAD", "BAG", "BAR", "BAT", "BAY", "BED", "BEE", "BET", "BIG", "BIT", "BOW", "BOX", "BOY", "BUD", "BUG", "BUS", "BUT", "BUY",
            "CAB", "CAN", "CAP", "CAR", "CAT", "COD", "COT", "COW", "CRY", "CUB", "CUP", "CUT",
            "DAD", "DAM", "DAY", "DEN", "DEW", "DID", "DIE", "DIG", "DOC", "DOE", "DOG", "DOT", "DRY", "DUB", "DUD", "DUE", "DUG", "DYE",
            "EAR", "EAT", "EEL", "EGG", "ELF", "ELK", "ELM", "EMU", "END", "ERA", "EVE", "EWE", "EYE",
            "FAN", "FAR", "FAT", "FAX", "FED", "FEE", "FEW", "FIG", "FIN", "FIR", "FIT", "FIX", "FLY", "FOE", "FOG", "FOR", "FOX", "FRY", "FUN", "FUR",
            "GAB", "GAG", "GAL", "GAP", "GAS", "GAY", "GEL", "GEM", "GET", "GIG", "GIN", "GNU", "GOD", "GOT", "GUM", "GUN", "GUT", "GUY", "GYM",
            "HAD", "HAM", "HAS", "HAT", "HAY", "HEM", "HEN", "HER", "HEW", "HEX", "HEY", "HID", "HIM", "HIP", "HIS", "HIT", "HOB", "HOG", "HOP", "HOT", "HOW", "HUB", "HUE", "HUG", "HUM", "HUT",
            # Common 4-letter words
            "ABLE", "ACHE", "ACID", "ACRE", "AGED", "AIDE", "ALSO", "AREA", "ARMY", "AUNT", "AUTO", "AWAY",
            "BABY", "BACK", "BAIL", "BAIT", "BAKE", "BALL", "BAND", "BANK", "BARE", "BARK", "BARN", "BASE", "BATH", "BEAM", "BEAN", "BEAR", "BEAT", "BEEN", "BEER", "BELL", "BELT", "BEND", "BEST", "BIKE", "BILL", "BIRD", "BITE", "BLOW", "BLUE", "BOAT", "BODY", "BOIL", "BOLD", "BOLT", "BOMB", "BOND", "BONE", "BOOK", "BOOM", "BOOT", "BORE", "BORN", "BOSS", "BOTH", "BOWL", "BURN", "BUSY",
            "CAFE", "CAGE", "CAKE", "CALL", "CALM", "CAME", "CAMP", "CANE", "CAPE", "CARD", "CARE", "CART", "CASE", "CASH", "CAST", "CAVE", "CELL", "CHAT", "CHEF", "CHIN", "CHIP", "CITY", "CLAP", "CLAY", "CLIP", "CLUB", "CLUE", "COAL", "COAT", "CODE", "COIL", "COIN", "COLD", "COLT", "COMB", "COME", "CONE", "COOK", "COOL", "COPE", "COPY", "CORD", "CORE", "CORK", "CORN", "COST", "CRAB", "CREW", "CROP", "CROW", "CUBE", "CURE", "CURL",
            "DALE", "DAME", "DAMP", "DARE", "DARK", "DART", "DATE", "DAWN", "DEAD", "DEAF", "DEAL", "DEAN", "DEAR", "DEBT", "DECK", "DEED", "DEEP", "DEER", "DEMO", "DENY", "DESK", "DIAL", "DICE", "DIET", "DIME", "DINE", "DIRT", "DISC", "DISH", "DIVE", "DOCK", "DOLL", "DOME", "DONE", "DOOR", "DOSE", "DOVE", "DOWN", "DOZE", "DRAG", "DRAW", "DREW", "DRIP", "DROP", "DRUG", "DRUM", "DUAL", "DUCK", "DUCT", "DUEL", "DUKE", "DULL", "DUMB", "DUMP", "DUNE", "DUNK", "DUSK", "DUST", "DUTY",
            "EACH", "EARL", "EARN", "EASE", "EAST", "EASY", "ECHO", "EDGE", "EDIT", "ELSE", "EMIT", "EPIC", "EVEN", "EVER", "EVIL", "EXAM", "EXIT", "EXPO",
            "FACE", "FACT", "FADE", "FAIL", "FAIR", "FALL", "FAME", "FARE", "FARM", "FAST", "FATE", "FEAR", "FEAT", "FEED", "FEEL", "FEET", "FELL", "FELT", "FILE", "FILL", "FILM", "FIND", "FINE", "FIRE", "FIRM", "FISH", "FIST", "FIVE", "FLAG", "FLAT", "FLAW", "FLEE", "FLEW", "FLIP", "FLOW", "FLUX", "FOAL", "FOAM", "FOLK", "FOND", "FONT", "FOOD", "FOOL", "FOOT", "FORD", "FORE", "FORK", "FORM", "FORT", "FOUL", "FOUR", "FOWL", "FREE", "FROG", "FROM", "FUEL", "FULL", "FUND", "FURY", "FUSE", "FUSS",
            # Common 5-letter words
            "ABOUT", "ABOVE", "ABUSE", "ACTOR", "ACUTE", "ADMIT", "ADOPT", "ADULT", "AFTER", "AGAIN", "AGENT", "AGREE", "AHEAD", "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIGN", "ALIKE", "ALIVE", "ALLOW", "ALONE", "ALONG", "ALTER", "ANGEL", "ANGER", "ANGLE", "ANGRY", "APART", "APPLE", "APPLY", "ARENA", "ARGUE", "ARISE", "ARMED", "ARMOR", "ARRAY", "ARROW", "ASSET", "AVOID", "AWAKE", "AWARD", "AWARE",
            "BADGE", "BADLY", "BAKER", "BASIC", "BEACH", "BEGAN", "BEGIN", "BEING", "BELOW", "BENCH", "BILLY", "BIRTH", "BLACK", "BLADE", "BLAME", "BLANK", "BLAST", "BLEED", "BLESS", "BLIND", "BLOCK", "BLOOD", "BLOOM", "BOARD", "BOOST", "BOOTH", "BOUND", "BRAIN", "BRAND", "BRAVE", "BREAD", "BREAK", "BREED", "BRICK", "BRIDE", "BRIEF", "BRING", "BROAD", "BROKE", "BROWN", "BRUSH", "BUILD", "BUILT", "BURST",
            "CABIN", "CABLE", "CAMEL", "CANAL", "CANDY", "CANOE", "CARGO", "CAROL", "CARRY", "CARVE", "CATCH", "CAUSE", "CEDAR", "CHAIN", "CHAIR", "CHALK", "CHANT", "CHAOS", "CHARM", "CHART", "CHASE", "CHEAP", "CHEAT", "CHECK", "CHEEK", "CHESS", "CHEST", "CHIEF", "CHILD", "CHINA", "CHOSE", "CIVIL", "CLAIM", "CLAMP", "CLASS", "CLEAN", "CLEAR", "CLERK", "CLICK", "CLIFF", "CLIMB", "CLOCK", "CLOSE", "CLOTH", "CLOUD", "CLOWN", "COACH", "COAST", "COLON", "COLOR", "CORAL", "COUCH", "COULD", "COUNT", "COURT", "COVER", "CRACK", "CRAFT", "CRANE", "CRASH", "CRAZY", "CREAM", "CREEK", "CRIME", "CRISP", "CROSS", "CROWD", "CROWN", "CRUDE", "CRUSH", "CURVE", "CYCLE",
            # More varied words
            "DAILY", "DAIRY", "DANCE", "DEALT", "DEATH", "DEBUT", "DELAY", "DELTA", "DENSE", "DEPTH", "DEVIL", "DIARY", "DIGIT", "DIRTY", "DOUBT", "DOUGH", "DOZEN", "DRAFT", "DRAIN", "DRAMA", "DRANK", "DRAWN", "DREAM", "DRESS", "DRIED", "DRILL", "DRINK", "DRIVE", "DROWN", "DRUMS",
            "EAGER", "EAGLE", "EARLY", "EARTH", "EIGHT", "ELBOW", "ELDER", "ELECT", "EMPTY", "ENEMY", "ENJOY", "ENTER", "ENTRY", "EQUAL", "ERROR", "ESSAY", "ETHIC", "EVENT", "EVERY", "EXACT", "EXCEL", "EXIST", "EXTRA",
            "FABLE", "FAITH", "FALSE", "FANCY", "FATAL", "FAULT", "FAVOR", "FEAST", "FENCE", "FERRY", "FEVER", "FIBER", "FIELD", "FIFTH", "FIFTY", "FIGHT", "FINAL", "FIRST", "FLAME", "FLASH", "FLEET", "FLESH", "FLOAT", "FLOOD", "FLOOR", "FLOUR", "FLUID", "FLUTE", "FOCUS", "FORCE", "FORTH", "FORTY", "FORUM", "FOUND", "FRAME", "FRANK", "FRAUD", "FRESH", "FRIED", "FRONT", "FROST", "FRUIT", "FULLY",
            "GIANT", "GIVEN", "GLAND", "GLASS", "GLOBE", "GLORY", "GLOVE", "GOING", "GRACE", "GRADE", "GRAIN", "GRAND", "GRANT", "GRAPE", "GRAPH", "GRASP", "GRASS", "GRAVE", "GREAT", "GREED", "GREEN", "GREET", "GRIEF", "GRILL", "GRIND", "GROSS", "GROUP", "GROVE", "GROWN", "GUARD", "GUESS", "GUEST", "GUIDE", "GUILD", "GUILT", "HABIT", "HAPPY", "HARSH", "HASTE", "HEART", "HEAVY", "HEDGE", "HELLO", "HENCE", "HONOR", "HORSE", "HOTEL", "HOUSE", "HUMAN", "HUMOR",
            "IDEAL", "IMAGE", "INDEX", "INNER", "INPUT", "IRONY", "ISSUE", "IVORY",
            "JEWEL", "JOINT", "JOKER", "JUDGE", "JUICE", "KNEEL", "KNIFE", "KNOWN",
            "LABEL", "LABOR", "LARGE", "LASER", "LATER", "LAUGH", "LAYER", "LEARN", "LEASE", "LEAST", "LEAVE", "LEGAL", "LEMON", "LEVEL", "LIGHT", "LIMIT", "LINEN", "LIVER", "LOCAL", "LODGE", "LOGIC", "LOOSE", "LOWER", "LOYAL", "LUCKY", "LUNAR", "LUNCH", "LYING",
            "MAGIC", "MAJOR", "MAKER", "MANOR", "MAPLE", "MARCH", "MARSH", "MATCH", "MAYBE", "MAYOR", "MEANS", "MEDIA", "MELON", "MERCY", "MERIT", "MERRY", "METAL", "METER", "METRO", "MIGHT", "MINOR", "MINUS", "MIXED", "MODEL", "MONEY", "MONTH", "MORAL", "MOTOR", "MOUNT", "MOUSE", "MOUTH", "MOVIE", "MUSIC",
            # 6-letter words
            "ABSORB", "ABROAD", "ACCEPT", "ACCESS", "ACCORD", "ACROSS", "ACTION", "ACTIVE", "ACTUAL", "ADVICE", "AFFECT", "AFFORD", "AFRAID", "AGENCY", "AGENDA", "ALMOST", "ALWAYS", "AMOUNT", "ANIMAL", "ANNUAL", "ANSWER", "ANYONE", "ANYWAY", "APPEAL", "APPEAR", "AROUND", "ARRIVE", "ARTIST", "ASPECT", "ASSESS", "ASSIGN", "ASSIST", "ASSUME", "ASSURE", "ATTACH", "ATTACK", "ATTEND", "AUTHOR", "AVENUE", "BALLOT", "BATTLE", "BEAUTY", "BECAME", "BECOME", "BEFORE", "BEHALF", "BEHIND", "BELIEF", "BELONG", "BESIDE", "BETTER", "BEYOND", "BISHOP", "BORDER", "BOTTLE", "BOTTOM", "BRANCH", "BREATH", "BRIDGE", "BRIGHT", "BROKEN", "BUDGET", "BURDEN", "BUREAU", "BUTTON", "CAMERA", "CANCER", "CANNOT", "CANVAS", "CARBON", "CAREER", "CASTLE", "CASUAL", "CAUGHT", "CENTER", "CENTRE", "CHANCE", "CHANGE", "CHARGE", "CHOICE", "CHOOSE", "CHOSEN", "CHROME", "CHURCH", "CINEMA", "CIRCLE", "CLINIC", "CLOSED", "CLOSER", "COFFEE", "COLUMN", "COMBAT", "COMING", "COMMIT", "COMMON", "COMPLY", "COPPER", "CORNER", "COTTON", "COUNTY", "COUPLE", "COURSE", "COUSIN", "CRISIS", "CUSTOM", "DAMAGE", "DANGER", "DEALER", "DEBATE", "DECADE", "DEFEAT", "DEFEND", "DEFINE", "DEGREE", "DEMAND", "DEPEND", "DEPUTY", "DESERT", "DESIGN", "DESIRE", "DETAIL", "DETECT", "DEVICE", "DEVOTE", "DIFFER", "DINNER", "DIRECT", "DIVIDE", "DOCTOR", "DOLLAR", "DOMAIN", "DOUBLE", "DRIVEN", "DRIVER", "DURING", "EASILY", "EATING", "EDITOR", "EFFECT", "EFFORT", "EITHER", "ELEVEN", "EMERGE", "EMPIRE", "EMPLOY", "ENABLE", "ENDING", "ENERGY", "ENGAGE", "ENGINE", "ENOUGH", "ENSURE", "ENTIRE", "ENTITY", "EQUITY", "ESCAPE", "ESTATE", "ETHNIC", "EUROPE", "EVOLVE", "EXCEED", "EXCEPT", "EXCUSE", "EXPAND", "EXPECT", "EXPERT", "EXPORT", "EXPOSE", "EXTENT", "FABRIC", "FACING", "FACTOR", "FAILED", "FAIRLY", "FALLEN", "FAMILY", "FAMOUS", "FATHER", "FELLOW", "FEMALE", "FIGURE", "FILING", "FINGER", "FINISH", "FISCAL", "FLYING", "FOLLOW", "FOREST", "FORGET", "FORMAL", "FORMAT", "FORMER", "FOSTER", "FOUGHT", "FOURTH", "FREEZE", "FRENCH", "FRIEND", "FROZEN", "FUTURE", "GALAXY", "GARAGE", "GARDEN", "GATHER", "GENDER", "GENTLE", "GERMAN", "GIVING", "GLOBAL", "GOLDEN", "GOTTEN", "GOVERN", "GROUND", "GROWTH", "GUITAR", "HANDLE", "HAPPEN", "HARDLY", "HATRED", "HEADED", "HEALTH", "HEIGHT", "HELMET", "HIDDEN", "HOLDER", "HONEST", "HORROR", "IMPACT", "IMPORT", "IMPOSE", "INCOME", "INDEED", "INDIAN", "INJURY", "INSIDE", "INTEND", "INTENT", "INVEST", "ISLAND", "ITSELF", "JACKET", "JERSEY", "JOSEPH", "JUNIOR", "KEEPER", "LATELY", "LATTER", "LAUNCH", "LAWYER", "LEADER", "LEAGUE", "LEAVES", "LENGTH", "LESSON", "LETTER", "LIFTED", "LIKELY", "LINKED", "LIQUID", "LISTEN", "LIVING", "LOADED", "LOCATE", "LOCKED", "LONDON", "LOSING", "LOVELY", "LOVING", "LOYALTY", "LUXURY", "MAINLY", "MANAGE", "MANNER", "MARGIN", "MARINE", "MARKED", "MARKET", "MASTER", "MATTER", "MATURE", "MEDIUM", "MEMBER", "MEMORY", "MENTAL", "MERELY", "METHOD", "MEXICO", "MIDDLE", "MINUTE", "MIRROR", "MISSED", "MOBILE", "MODERN", "MODEST", "MODULE", "MOMENT", "MOTHER", "MOTION", "MOVING", "MURDER", "MUSEUM", "MUTUAL", "MYSELF", "NARROW", "NATION", "NATIVE", "NATURE", "NEARBY", "NEARLY", "NEEDLE", "NEEDED", "NEPHEW", "NICELY", "NOBODY", "NORMAL", "NOTICE", "NOTION", "NUMBER", "OBJECT", "OBTAIN", "OCCUPY", "OCCUR", "OFFICE", "OFFSET", "ONLINE", "OPENED", "OPPOSE", "OPTION", "ORANGE", "ORIGIN", "OUTPUT", "OVERALL", "OXFORD", "PACKED", "PALACE", "PARENT", "PARTLY", "PASSED", "PATENT", "PAYING", "PENCIL", "PEOPLE", "PERIOD", "PERMIT", "PERSON", "PHRASE", "PICKED", "PLANET", "PLAYER", "PLEASE", "PLENTY", "POCKET", "POETRY", "POISON", "POLICE", "POLICY", "POLISH", "PORTAL", "POTATO", "POWDER", "PRAISE", "PREFER", "PRETTY", "PRIEST", "PRINCE", "PRISON", "PROFIT", "PROMPT", "PROPER", "PROVEN", "PUBLIC", "PURELY", "PURPLE", "PURSUE", "PUZZLE", "QUAINT", "QUEEN", "RABBIT", "RACING", "RAISED", "RANDOM", "RARELY", "RATHER", "RATING", "READER", "REALLY", "REASON", "RECALL", "RECENT", "RECORD", "REDUCE", "REFORM", "REFUSE", "REGARD", "REGIME", "REGION", "REGRET", "REJECT", "RELATE", "RELIEF", "REMAIN", "REMARK", "REMIND", "REMOTE", "REMOVE", "RENTAL", "REPAIR", "REPEAT", "REPLY", "REPORT", "RESCUE", "RESIST", "RESORT", "RESULT", "RETAIL", "RETAIN", "RETIRE", "RETURN", "REVEAL", "REVIEW", "REWARD", "RISING", "RITUAL", "ROCKET", "ROLLED", "RUBBER", "RULING", "SAFELY", "SAFETY", "SAILING", "SALARY", "SAMPLE", "SAVING", "SAYING", "SCHEME", "SCHOOL", "SCIENCE", "SCREEN", "SCRIPT", "SEARCH", "SEASON", "SECOND", "SECRET", "SECTOR", "SECURE", "SEEING", "SELECT", "SELLER", "SENATE", "SENIOR", "SENSOR", "SERIES", "SERVED", "SERVER", "SETTLE", "SEVERE", "SEXUAL", "SHAPED", "SHARED", "SHIELD", "SHIFT", "SHIRT", "SHOOT", "SHOP", "SHORE", "SHORTS", "SHOULD", "SHOWER", "SHOWED", "SHRINE", "SIGNAL", "SIGNED", "SILENT", "SILVER", "SIMPLE", "SIMPLY", "SINGER", "SINGLE", "SISTER", "SITTING", "SKETCH", "SLIGHT", "SMOOTH", "SOCCER", "SOCIAL", "SOCKET", "SODIUM", "SOLELY", "SOLVED", "SOURCE", "SOVIET", "SPEECH", "SPIRIT", "SPOKEN", "SPREAD", "SPRING", "SQUARE", "STABLE", "STANCE", "STATED", "STATUS", "STAYED", "STEADY", "STOLEN", "STORED", "STORM", "STORY", "STRAIN", "STRAND", "STREAM", "STREET", "STRESS", "STRICT", "STRIKE", "STRING", "STROKE", "STRONG", "STRUCK", "STUDIO", "STUPID", "SUBMIT", "SUDDEN", "SUFFER", "SUMMER", "SUMMIT", "SUNDAY", "SUNSET", "SUPPLY", "SURELY", "SURVEY", "SWITCH", "SYMBOL", "SYSTEM", "TABLET", "TACTIC", "TAKING", "TALENT", "TARGET", "TAUGHT", "TEMPLE", "TENANT", "TENDER", "TENNIS", "TERROR", "THANKS", "THEORY", "THIRTY", "THOUGH", "THREAD", "THREAT", "THROAT", "THROWN", "THRUST", "TICKET", "TIMBER", "TIMING", "TISSUE", "TITLED", "TOILET", "TONGUE", "TOWARD", "TRACKS", "TRADER", "TRAGIC", "TRAVEL", "TREATY", "TREATY", "TRIPLE", "TROPHY", "TRUCK", "TRYING", "TUNNEL", "TURKEY", "TURNED", "TWELVE", "TWENTY", "UNABLE", "UNFAIR", "UNIQUE", "UNITED", "UNLESS", "UNLIKE", "UNPAID", "UPDATE", "UPLOAD", "UPPER", "URBAN", "USEFUL", "VALLEY", "VARIED", "VENDOR", "VICTIM", "VIEWER", "VIOLET", "VIRTUE", "VISION", "VISUAL", "VOLUME", "VOTERS", "VOTING", "WAITED", "WALKED", "WALLET", "WANTED", "WARDEN", "WARMTH", "WARNED", "WEALTH", "WEAPON", "WEEKLY", "WEIGHT", "WHOLLY", "WICKED", "WIDELY", "WIDGET", "WINDOW", "WINNER", "WINTER", "WISDOM", "WOODEN", "WORKER", "WORKS", "WRITER", "YELLOW", "YOUNGER",
            # 7-letter words
            "ABILITY", "ABSENCE", "ACADEMY", "ACCOUNT", "ACCUSED", "ACHIEVE", "ACQUIRE", "ADDRESS", "ADVANCE", "ADVERSE", "ADVISER", "AGAINST", "AIRCRAFT", "AIRPORT", "ALCOHOL", "ALLEGED", "ALREADY", "ANALYST", "ANCIENT", "ANOTHER", "ANXIETY", "ANXIOUS", "ANYBODY", "ANYMORE", "ANYTHING", "APPLIED", "APPOINT", "APPROVE", "ARRANGE", "ARRIVAL", "ARTICLE", "ARTIST", "ASSAULT", "ASSUMED", "ASSURED", "ATHLETE", "ATTEMPT", "ATTRACT", "AUCTION", "AVERAGE", "BALANCE", "BARRIER", "BATTERY", "BEARING", "BEATING", "BECAUSE", "BEDROOM", "BENEFIT", "BENEATH", "BESIDES", "BETWEEN", "BICYCLE", "BILLION", "BINDING", "BIOLOGY", "BLANKET", "BLOWING", "BORROW", "BROTHER", "BROUGHT", "BUILDER", "BURNING", "CABINET", "CALIBER", "CALLING", "CAPITAL", "CAPTION", "CAPTURE", "CAREFUL", "CARRIER", "CARTOON", "CATALOG", "CAUTION", "CEILING", "CENTRAL", "CENTURY", "CERAMIC", "CERTAIN", "CHAMBER", "CHANGED", "CHANNEL", "CHAPTER", "CHARITY", "CHARLIE", "CHARTER", "CHECKED", "CHICKEN", "CIRCUIT", "CITIZEN", "CLARITY", "CLASSIC", "CLIMATE", "CLOSING", "CLOTHES", "CLUSTER", "COASTAL", "COLLECT", "COLLEGE", "COMBINE", "COMFORT", "COMMAND", "COMMENT", "COMPACT", "COMPANY", "COMPARE", "COMPETE", "COMPILE", "COMPLEX", "CONCEPT", "CONCERN", "CONCERT", "CONDUCT", "CONFIRM", "CONFLICT", "CONNECT", "CONSENT", "CONSIST", "CONSOLE", "CONTACT", "CONTAIN", "CONTENT", "CONTEST", "CONTEXT", "CONTROL", "CONVERT", "COOKING", "COOLING", "COUNSEL", "COUNTER", "COUNTRY", "COURAGE", "COVERED", "CREATED", "CREATOR", "CRICKET", "CRUCIAL", "CRYSTAL", "CULTURE", "CURIOUS", "CURRENT", "CURTAIN", "CUTTING", "DEALING", "DECIDED", "DECLINE", "DEFAULT", "DEFENSE", "DEFICIT", "DELIVER", "DENSITY", "DEPOSIT", "DESKTOP", "DESPITE", "DESTROY", "DEVELOP", "DEVOTED", "DIAGRAM", "DIAMOND", "DIGITAL", "DINING", "DIPLOMA", "DISABLE", "DISASTER", "DISCUSS", "DISEASE", "DISMISS", "DISPLAY", "DISPUTE", "DISTANT", "DIVERSE", "DIVIDED", "DIVORCE", "DOCTORS", "DRAWING", "DRESSED", "DRIVING", "DROPPING", "EASTERN", "ECONOMY", "EDITION", "ELDERLY", "ELECTED", "ELEMENT", "EMBASSY", "EMOTION", "EMPEROR", "ENHANCE", "ENJOYED", "ENTERED", "EPISODE", "ESSENCE", "EVENING", "EVIDENT", "EXACTLY", "EXAMINE", "EXAMPLE", "EXCITED", "EXCLUDE", "EXECUTE", "EXHIBIT", "EXPENSE", "EXPLAIN", "EXPLORE", "EXPRESS", "EXTREME", "FACULTY", "FAILURE", "FALLING", "FAMILIAR", "FANTASY", "FASHION", "FEATURE", "FEDERAL", "FEELING", "FICTION", "FIFTEEN", "FIGHTER", "FILLING", "FINANCE", "FINDING", "FISHING", "FITNESS", "FLORIDA", "FLOWING", "FOREIGN", "FOREVER", "FORMULA", "FORTUNE", "FORWARD", "FOUNDER", "FREEDOM", "FREIGHT", "FUNDING", "FURTHER", "GALLERY", "GARBAGE", "GENERAL", "GENETIC", "GENUINE", "GETTING", "GODDESS", "GRADUATE", "GRAMMAR", "GRANTED", "GRAPHIC", "GRAVITY", "GREATER", "GROUND", "GROWING", "GUARDED", "GUIDANCE", "HABITAT", "HALFWAY", "HANGING", "HAPPEN", "HEADING", "HEALTHY", "HEARING", "HEATING", "HEAVILY", "HELPFUL", "HERSELF", "HIGHWAY", "HIMSELF", "HISTORY", "HITTING", "HOLDING", "HOLIDAY", "HORIZON", "HOSTILE", "HOUSING", "HOWEVER", "HUNDRED", "HUSBAND", "IMAGINE", "IMPLIED", "IMPROVE", "IMPULSE", "INCLUDE", "INITIAL", "INQUIRY", "INSIGHT", "INSPIRE", "INSTALL", "INSTANT", "INSTEAD", "INTEGER", "INTENSE", "INTERIM", "ISRAELI", "ITALIAN", "JACQUES", "JEWELRY", "JOINING", "JOURNEY", "JUSTICE", "JUSTIFY", "KEEPING", "KEYWORD", "KILLING", "KINGDOM", "KITCHEN", "KNOWING", "LABELED", "LANDING", "LARGELY", "LASTING", "LEADING", "LEARNED", "LEAVING", "LECTURE", "LIBERAL", "LIBRARY", "LICENSE", "LIFELONG", "LIFTING", "LIMITED", "LINKING", "LISTING", "LITERAL", "LOADING", "LOCATED", "LOCKING", "LOOKING", "LOYALTY", "MACHINE", "MANAGER", "MARRIED", "MASSIVE", "MASTERS", "MATCHED", "MAXIMUM", "MEANING", "MEASURE", "MEDICAL", "MEETING", "MENTAL", "MESSAGE", "MILLION", "MINERAL", "MINIMAL", "MINIMUM", "MISSING", "MISSION", "MISTAKE", "MIXTURE", "MONITOR", "MONTHLY", "MORNING", "MOUNTED", "MYSTERY", "NATURAL", "NEAREST", "NEITHER", "NERVOUS", "NETWORK", "NEUTRAL", "NUCLEAR", "NOWHERE", "NURSERY", "NURSING", "OBVIOUS", "OCTOBER", "OFFENSE", "OFFICER", "OPENING", "OPERATE", "OPINION", "OPTICAL", "ORGANIC", "OUTDOOR", "OUTLINE", "OUTSIDE", "OVERALL", "PACKAGE", "PAINTED", "PARKING", "PARTIAL", "PARTNER", "PASSAGE", "PASSING", "PASSION", "PASSIVE", "PATIENT", "PATRICK", "PATTERN", "PAYMENT", "PENALTY", "PERCENT", "PERFECT", "PERFORM", "PERHAPS", "PERSIST", "PERSONS", "Phoenix", "PICTURE", "PIONEER", "PLASTIC", "PLEASED", "POINTER", "POPULAR", "PORTION", "POVERTY", "PRECISE", "PREDICT", "PREMIER", "PREMIUM", "PREPARE", "PRESENT", "PREVENT", "PRIMARY", "PRINTER", "PRIVACY", "PRIVATE", "PROBLEM", "PROCEED", "PROCESS", "PRODUCE", "PRODUCT", "PROFILE", "PROGRAM", "PROJECT", "PROMISE", "PROMOTE", "PROTECT", "PROTEIN", "PROTEST", "PROVIDE", "PUBLISH", "PURCHASE", "PURSUIT", "PYRAMID", "QUALITY", "QUANTUM", "QUARTER", "QUICKLY", "RADICAL", "RAILWAY", "RAINBOW", "RAISING", "RANGING", "RANKING", "RAPIDLY", "READILY", "READING", "REALITY", "REALIZE", "RECEIPT", "RECEIVE", "RECENTLY", "RECOGNIZE", "RECOVER", "REDUCED", "REFLECT", "REFUSED", "REGULAR", "RELATED", "REMAINS", "REMOVAL", "REMOVED", "REPLACE", "REPLIED", "REQUEST", "REQUIRE", "RESERVE", "RESIDENT", "RESPECT", "RESPOND", "RESTORE", "RETIRED", "RETREAT", "RETURNS", "REVENUE", "REVERSE", "REVISED", "RICARDO", "RICHARD", "ROLLING", "ROUTINE", "RUNNING", "RUSSIAN", "SATISFY", "SAVINGS", "SCANDAL", "SCENARIO", "SCIENCE", "SCRATCH", "SECTION", "SEGMENT", "SELLING", "SENDING", "SENATOR", "SENTENCE", "SERIOUS", "SERVANT", "SERVICE", "SESSION", "SETTING", "SETTLED", "SEVERAL", "SHELTER", "SHERIFF", "SHIFTED", "SHIPPING", "SHORTLY", "SHOWING", "SILENCE", "SIMILAR", "SITTING", "SIXTEEN", "SKILLED", "SMOKING", "SOCIETY", "SOMEHOW", "SOMEONE", "SOMEWHAT", "SORTING", "SPEAKER", "SPECIAL", "SPECIES", "SPOTTED", "SQUEEZE", "STADIUM", "STANLEY", "STARTED", "STATION", "STATUTE", "STAYING", "STEPHEN", "STORAGE", "STRANGE", "STRETCH", "STUDENT", "STUDIED", "STUDIES", "SUBJECT", "SUCCEED", "SUCCESS", "SUGGEST", "SUMMARY", "SUPPORT", "SUPPOSE", "SUPREME", "SURFACE", "SURGERY", "SURPLUS", "SURVIVE", "SUSPECT", "SUSTAIN", "SYMBOLS", "SYSTEMS", "TACTICAL", "TALKING", "TARGETS", "TEACHER", "TELLING", "TENSION", "TERRACE", "TERRAIN", "TESTING", "TEXTURE", "THEATER", "THERAPY", "THEREBY", "THERMAL", "THOUGHT", "THREADS", "THREATS", "THROUGH", "THUNDER", "TONIGHT", "TOTALLY", "TOUCHED", "TOURIST", "TOWARDS", "TRADING", "TRAFFIC", "TRAILER", "TRAINED", "TREATED", "TRIBUNE", "TROUBLE", "TURNING", "TYPICAL", "UNDERGO", "UNIFORM", "UNKNOWN", "UNUSUAL", "UPDATED", "UPGRADE", "UPRIGHT", "UTILITY", "UNKNOWN", "VARIOUS", "VEHICLE", "VENTURE", "VERSION", "VETERAN", "VICTIMS", "VICTORY", "VIETNAM", "VILLAGE", "VINTAGE", "VIOLENT", "VIRTUAL", "VISIBLE", "VISITED", "VISITOR", "VITAMIN", "VOLUMES", "WAITING", "WALKING", "WANTING", "WARNING", "WARRIOR", "WASHING", "WATCHED", "WEALTHY", "WEATHER", "WEDDING", "WEEKEND", "WELCOME", "WELFARE", "WESTERN", "WHETHER", "WILLING", "WINNING", "WINSTON", "WITHOUT", "WITNESS", "WORKING", "WORRIED", "WORSHIP", "WRITING", "WRITTEN", "YOUNGER",
            # 8+ letter words
            "ABSOLUTE", "ABSTRACT", "ACADEMIC", "ACCEPTED", "ACCIDENT", "ACHIEVED", "ACQUIRED", "ACTUALLY", "ADDITION", "ADEQUATE", "ADJACENT", "ADJUSTED", "ADVANCED", "ADVISORY", "ADVOCATE", "AFFECTED", "AIRCRAFT", "ALTHOUGH", "ANALYSIS", "ANNOUNCE", "ANYTHING", "ANYWHERE", "APPARENT", "APPEARED", "APPROACH", "APPROVAL", "ARGUMENT", "ARRESTED", "ARTICLES", "ASSEMBLY", "ASSUMING", "ATHLETIC", "ATTACHED", "ATTORNEY", "AUDIENCE", "AVAILABLE", "AVIATION", "BACHELOR", "BACTERIA", "BASEBALL", "BATHROOM", "BECOMING", "BEHAVIOR", "BELIEVED", "BENEFITS", "BOUNDARY", "BREAKING", "BREATHING", "BRINGING", "BROTHERS", "BUILDING", "BUSINESS", "CALENDAR", "CAMPAIGN", "CAPACITY", "CAPTURED", "CARRYING", "CATEGORY", "CATHOLIC", "CAUTIOUS", "CELEBRATE", "CEMETERY", "CEREMONY", "CHAIRMAN", "CHAMPION", "CHANGING", "CHANNELS", "CHARACTER", "CHEMICAL", "CHILDREN", "CIRCULAR", "CIVILIAN", "CLAIMING", "CLINICAL", "CLOTHING", "COLONIAL", "COMBINED", "COMMANDS", "COMMERCE", "COMMERCIAL", "COMMISSION", "COMMITTED", "COMMITTEE", "COMMUNAL", "COMMUNITY", "COMPARED", "COMPLAIN", "COMPLETE", "COMPOSED", "COMPOUND", "COMPRISE", "COMPUTER", "CONCLUDED", "CONCRETE", "CONFLICT", "CONFUSED", "CONGRESS", "CONQUEST", "CONSIDER", "CONSUMER", "CONTACTS", "CONTEMPT", "CONTENTS", "CONTINUE", "CONTRACT", "CONTRAST", "CONVINCE", "CORRIDOR", "COVERAGE", "CREATION", "CREATIVE", "CREATURE", "CRIMINAL", "CRITICAL", "CROSSING", "CULTURAL", "CURRENCY", "CUSTOMER", "DATABASE", "DAUGHTER", "DAYLIGHT", "DEADLINE", "DECIDING", "DECISION", "DECLARED", "DECREASE", "DELICATE", "DELIVERY", "DEMOCRAT", "DESCRIBE", "DESIGNED", "DETAILED", "DIABETES", "DIAMETER", "DIAMOND", "DICTATOR", "DIRECTLY", "DIRECTOR", "DISABLED", "DISASTER", "DISCLOSED", "DISCOUNT", "DISCOVER", "DISORDER", "DISTANCE", "DISTINCT", "DISTRICT", "DIVIDING", "DIVISION", "DOCTRINE", "DOCUMENT", "DOMINANT", "DRAMATIC", "DURATION", "ECONOMIC", "EDUCATED", "EIGHTEEN", "ELECTION", "ELECTRIC", "ELECTRON", "ELEMENTS", "ELEPHANT", "ELIGIBLE", "EMISSION", "EMOTIONAL", "EMPHASIS", "EMPLOYEE", "EMPLOYER", "ENGAGING", "ENGINEER", "ENORMOUS", "ENTIRELY", "ENTRANCE", "ENVELOPE", "EQUALITY", "EQUATION", "EQUIPPED", "ESTIMATE", "EUROPEAN", "EVALUATE", "EVENTUAL", "EVERYONE", "EVIDENCE", "EXCHANGE", "EXCITING", "EXERCISE", "EXPLICIT", "EXPOSURE", "EXTENDED", "EXTERNAL", "FACILITY", "FAMILIAR", "FAVORITE", "FEATURED", "FEBRUARY", "FEEDBACK", "FESTIVAL", "FIGHTING", "FINISHED", "FLOATING", "FOLLOWED", "FOOTBALL", "FORECAST", "FOREHEAD", "FORMALLY", "FORMERLY", "FRACTION", "FRAGMENT", "FRANKLY", "FREQUENT", "FRIENDLY", "FRONTIER", "FUNCTION", "GENERATE", "GENEROUS", "GORGEOUS", "GRADIENT", "GRADUATE", "GRAPHICS", "GRATEFUL", "GREATEST", "GUARDIAN", "GUIDANCE", "HANDLING", "HARDWARE", "HEADLINE", "HERITAGE", "HIGHLAND", "HISTORIC", "HOMELESS", "HONESTLY", "HOSPITAL", "HUMANITY", "HUNDREDS", "HYDROGEN", "IDENTIFY", "IDENTITY", "IDEOLOGY", "IGNORANT", "ILLUSION", "IMPERIAL", "IMPLICIT", "IMPORTED", "IMPROVED", "INCIDENT", "INCLUDED", "INCREASE", "INDICATE", "INDIRECT", "INDUSTRY", "INFERIOR", "INFINITE", "INFORMED", "INHERENT", "INNOCENT", "INSECT", "INSPIRED", "INSTANCE", "INSTINCT", "INTENDED", "INTEREST", "INTERIOR", "INTERNAL", "INTERVAL", "INTIMATE", "INVASION", "INVOLVED", "ISOLATED", "JUDGMENT", "JUNCTION", "KEYBOARD", "KISSED", "LANDMARK", "LANGUAGE", "LAUGHTER", "LAUNCHED", "LEARNING", "LIKEWISE", "LITERARY", "LOCATION", "MAGAZINE", "MAGNETIC", "MAINLAND", "MAINTAIN", "MAJORITY", "MANIFEST", "MARRIAGE", "MARRIED", "MATERIAL", "MATURITY", "MEASURED", "MECHANISM", "MEDIEVAL", "MEMORIAL", "MERCHANT", "MIDNIGHT", "MILITARY", "MINISTER", "MINORITY", "MODERATE", "MONUMENT", "MOREOVER", "MORTGAGE", "MOUNTAIN", "MOVEMENT", "MULTIPLE", "MUSCLES", "NATIONAL", "NATURALLY", "NEGATIVE", "NEIGHBOR", "NORTHERN", "NOVELIST", "NUMEROUS", "OBSERVER", "OBTAINED", "OCCASION", "OCCUPIED", "OFFENSE", "OFFICIAL", "OPERATED", "OPERATOR", "OPPONENT", "OPPOSITE", "OPTIMIZE", "OPTIONAL", "ORDINARY", "ORGANIZE", "ORIGINAL", "OUTBREAK", "OVERCOME", "OVERHEAD", "OVERSEAS", "OVERVIEW", "PAINTING", "PARALLEL", "PARTICLE", "PARTNER", "PASSPORT", "PASSWORD", "PATIENCE", "PEACEFUL", "PENTAGON", "PERCEIVED", "PERSONAL", "PERSUADE", "PETITION", "PHYSICAL", "PIPELINE", "PLATFORM", "PLEASANT", "PLEASURE", "POINTING", "POLITICS", "POSITIVE", "POSSIBLE", "POSSIBLY", "POWERFUL", "PRACTICE", "PRECEDED", "PRECIOUS", "PRECISE", "PREDICTED", "PREGNANT", "PREPARED", "PRESENCE", "PRESERVE", "PRESSURE", "PRINCESS", "PRINTING", "PRIORITY", "PRISONER", "PROBABLY", "PROCEDURE", "PRODUCED", "PRODUCER", "PROFOUND", "PROGRESS", "PROMISED", "PROPERTY", "PROPOSAL", "PROPOSED", "PROSPECT", "PROTOCOL", "PROVIDED", "PROVINCE", "PUBLICLY", "PURCHASE", "PURSUING", "QUESTION", "RATIONAL", "REACTION", "REALIZED", "REASONED", "RECEIVED", "RECENTLY", "RECEPTOR", "RECORDER", "RECOVERY", "REDIRECT", "REFERRED", "REGIONAL", "REGISTER", "REGULATE", "REJECTED", "RELATION", "RELATIVE", "RELEVANT", "RELIABLE", "RELIGION", "REMAINED", "REMEMBER", "REMOTELY", "RENDERED", "REPEATED", "REPLACED", "REPORTED", "REPUBLIC", "RESEARCH", "RESERVED", "RESIDENT", "RESOURCE", "RESPONSE", "RESTORED", "RESTRICT", "RETAINED", "RETURNED", "REVEALED", "REVENUES", "REVERSED", "REVIEWED", "REVISION", "ROMANTIC", "ROTATION", "SCENARIO", "SCHEDULE", "SCIENCES", "SCOTLAND", "SCREAMED", "SEARCHED", "SEASONAL", "SECONDLY", "SECRETLY", "SECURITY", "SELECTED", "SEMESTER", "SENTENCE", "SEPARATE", "SEQUENCE", "SERGEANT", "SEVERELY", "SHEPHERD", "SHIFTING", "SHOOTING", "SHOPPING", "SHORTAGE", "SHORTEST", "SHOULDER", "SHOWERED", "SHUTDOWN", "SICKNESS", "SILENCE", "SIMPLIFY", "SITUATED", "SLIGHTLY", "SOFTWARE", "SOLUTION", "SOMEBODY", "SOMEBODY", "SOMEHOW", "SOMEWHAT", "SOUTHERN", "SPEAKING", "SPECIFIC", "SPECIMEN", "SPECTRAL", "SPECTRUM", "SPELLING", "SPENDING", "SPIRITUAL", "SPLENDID", "SPORTING", "STANDARD", "STANDING", "STARTING", "STATEMENT", "STERLING", "STIMULUS", "STRAIGHT", "STRANGER", "STRATEGY", "STRENGTH", "STRICTLY", "STRIKING", "STRONGLY", "STRUGGLE", "STUDYING", "STUNNING", "SUBSTANTIAL", "SUBURBAN", "SUDDENLY", "SUFFERED", "SUPERIOR", "SUPPOSED", "SUPPRESS", "SURPRISE", "SURROUND", "SURVIVAL", "SUSPECTED", "SWIMMING", "SYMBOLIC", "SYNDROME", "TAXATION", "TEACHING", "TEAMWORK", "TECHNICAL", "TEENAGER", "TELEPHONE", "TELESCOPY", "TEMPLATE", "TEMPORAL", "TENDENCY", "TERRIBLE", "TERTIARY", "THAILAND", "THINKING", "THIRTEEN", "THOUSAND", "TOGETHER", "TOMORROW", "TOUCHING", "TRACKING", "TRADITION", "TRAINING", "TRANSFER", "TRANSMIT", "TRANSPORT", "TRAVELED", "TREASURE", "TREASURY", "TRIANGLE", "TRIBUNAL", "TRILLION", "TROPICAL", "TROUBLED", "ULTIMATE", "UMBRELLA", "UNIVERSE", "UNLIKELY", "UNSIGNED", "UPCOMING", "UPDATING", "UPSTAIRS", "VALUABLE", "VARIABLE", "VERTICAL", "VETERANS", "VICTORIA", "VIOLENCE", "VISITING", "VOLCANIC", "VOLTAGES", "WANDERED", "WARNINGS", "WARRANTY", "WATCHING", "WEAKNESS", "WEIGHTED", "WELCOMED", "WHATEVER", "WHENEVER", "WHEREVER", "WHISPERED", "WILDLIFE", "WILLIAMS", "WIRELESS", "WITHDREW", "WONDERFUL", "WOODLAND", "WORKSHOP", "WORLDWIDE", "WORRYING", "YOUNGEST"
        ]

    def _organize_by_difficulty(self) -> Dict[str, List[str]]:
        """Organize words by difficulty level"""
        easy = [w for w in self.all_words if 3 <= len(w) <= 5]
        medium = [w for w in self.all_words if 5 <= len(w) <= 8]
        hard = [w for w in self.all_words if 7 <= len(w) <= 15]

        return {
            "Monday": easy[:500],
            "Tuesday": easy[:300] + medium[:200],
            "Wednesday": medium[:400],
            "Thursday": medium[:300] + hard[:200],
            "Friday": hard[:400],
            "Saturday": hard[:500],
            "Sunday": medium[:300] + hard[:300]
        }

    def generate_simple_grid(self, size: Tuple[int, int] = (15, 15)) -> List[List[int]]:
        """
        Generate a simple crossword grid with rotational symmetry
        1 = white square, 0 = black square
        """
        n, m = size
        grid = [[1] * m for _ in range(n)]

        # Add black squares with symmetry
        num_black_squares = int(n * m * 0.15)  # ~15% black squares
        placed = 0

        while placed < num_black_squares // 2:
            i = random.randint(0, n - 1)
            j = random.randint(0, m - 1)

            # Don't place in corners or if already black
            if grid[i][j] == 0:
                continue

            # Place black square and its symmetric counterpart
            grid[i][j] = 0
            grid[n-1-i][m-1-j] = 0
            placed += 1

        return grid

    def generate_puzzle(
        self,
        puzzle_id: str,
        date: datetime,
        size: Tuple[int, int] = (15, 15),
        difficulty: Optional[str] = None
    ) -> Dict:
        """Generate a complete realistic synthetic puzzle"""

        if difficulty is None:
            difficulty = get_day_of_week(date)

        # Generate grid
        grid_layout = self.generate_simple_grid(size)
        grid_numbers = number_grid(grid_layout)

        # Extract word positions
        word_positions = extract_words_from_grid(grid_layout, grid_numbers)

        # Select theme
        theme_name = random.choice(list(self.themes.keys()))
        theme_words = self.themes[theme_name].copy()
        random.shuffle(theme_words)

        # Get word pool for difficulty
        word_pool = self.word_pools.get(difficulty, self.word_pools["Wednesday"])

        # Fill in answers
        answers = {"across": [], "down": []}
        clues = {"across": {}, "down": {}}
        theme_answers = []
        theme_word_index = 0

        # Across words
        for i, word_info in enumerate(word_positions["across"]):
            length = word_info["length"]

            # Determine if this should be a theme answer (select longer words for themes)
            is_theme = (theme_word_index < len(theme_words) and
                       length >= 4 and
                       i % 5 == 0 and  # Every 5th word could be theme
                       len(theme_answers) < 5)  # Limit theme answers

            if is_theme:
                # Try to find a matching theme word
                matching_theme = [w for w in theme_words[theme_word_index:] if len(w) == length]
                if matching_theme:
                    answer = matching_theme[0]
                    theme_word_index = theme_words.index(answer) + 1
                else:
                    is_theme = False

            if not is_theme:
                # Use regular word from pool
                answer = self._find_best_word(length, word_pool)

            answers["across"].append({
                "number": word_info["number"],
                "answer": answer,
                "start_pos": word_info["start_pos"],
                "length": length,
                "is_theme": is_theme
            })

            clues["across"][str(word_info["number"])] = self._generate_clue(
                answer, difficulty, theme_name if is_theme else None
            )

            if is_theme:
                theme_answers.append(answer)

        # Down words
        for i, word_info in enumerate(word_positions["down"]):
            length = word_info["length"]

            # Determine if this should be a theme answer
            is_theme = (theme_word_index < len(theme_words) and
                       length >= 4 and
                       i % 6 == 0 and  # Every 6th word could be theme
                       len(theme_answers) < 10)  # Limit total theme answers

            if is_theme:
                # Try to find a matching theme word
                matching_theme = [w for w in theme_words[theme_word_index:] if len(w) == length]
                if matching_theme:
                    answer = matching_theme[0]
                    theme_word_index = theme_words.index(answer) + 1
                else:
                    is_theme = False

            if not is_theme:
                # Use regular word from pool
                answer = self._find_best_word(length, word_pool)

            answers["down"].append({
                "number": word_info["number"],
                "answer": answer,
                "start_pos": word_info["start_pos"],
                "length": length,
                "is_theme": is_theme
            })

            clues["down"][str(word_info["number"])] = self._generate_clue(
                answer, difficulty, theme_name if is_theme else None
            )

            if is_theme:
                theme_answers.append(answer)

        # Construct puzzle
        puzzle = {
            "puzzle_id": puzzle_id,
            "date": date.strftime("%Y-%m-%d"),
            "day_of_week": difficulty,
            "size": list(size),
            "theme": theme_name,
            "grid": {
                "layout": grid_layout,
                "numbers": grid_numbers
            },
            "answers": answers,
            "clues": clues,
            "theme_answers": theme_answers,
            "stats": {
                "word_count": len(answers["across"]) + len(answers["down"]),
                "black_square_count": sum(row.count(0) for row in grid_layout),
                "has_symmetry": check_rotational_symmetry(grid_layout)
            },
            "source": "synthetic"
        }

        return puzzle

    def _find_best_word(self, length: int, word_pool: List[str]) -> str:
        """Find best matching word for given length, only return exact matches"""
        # First try from the word pool
        matching_words = [w for w in word_pool if len(w) == length]
        if matching_words:
            return random.choice(matching_words)

        # Fallback to words organized by length (exact match only)
        if length in self.words_by_length and self.words_by_length[length]:
            return random.choice(self.words_by_length[length])

        # Last resort: search all words for exact length match
        matching_all = [w for w in self.all_words if len(w) == length]
        if matching_all:
            return random.choice(matching_all)

        # If absolutely no words of this length exist, use a placeholder
        # (This should rarely happen with a good word list)
        logger.warning(f"No words found for length {length}, using placeholder")
        return "A" * length

    def _generate_clue(self, answer: str, difficulty: str, theme: Optional[str] = None) -> str:
        """Generate realistic clues for answers"""
        answer_lower = answer.lower()

        # Clue templates based on common crossword patterns
        if theme:
            theme_clues = {
                "Space": f"{answer.capitalize()} in astronomy",
                "Movies": f"Film term: {answer.lower()}",
                "Sports": f"Athletic competition term",
                "Music": f"Musical element",
                "Food": f"Culinary term",
                "Science": f"Scientific concept",
                "Ocean": f"Marine life or feature",
                "Nature": f"Natural phenomenon",
                "Travel": f"Journey-related term",
                "Books": f"Literary term",
                "Technology": f"Tech-related",
                "History": f"Historical term"
            }
            return theme_clues.get(theme, f"Related to {theme}")

        # Word-specific clues (simplified, real clues would be much more creative)
        specific_clues = {
            "ACTOR": "One in a cast",
            "MOVIE": "Theater showing",
            "PIANO": "Musical instrument with 88 keys",
            "OCEAN": "Atlantic or Pacific",
            "RIVER": "Flowing body of water",
            "TREE": "Oak or elm",
            "BIRD": "Robin or eagle",
            "BOOK": "Novel, for one",
            "MUSIC": "Symphony output",
            "SPORT": "Athletic activity",
            "BEACH": "Sandy shore",
            "HOUSE": "Place to live",
            "HAPPY": "Joyful",
            "WATER": "H2O",
            "EARTH": "Third rock from the sun",
            "DANCE": "Waltz or tango",
            "SMILE": "Grin",
            "FLOWER": "Rose or tulip",
            "HORSE": "Equine animal",
            "CLOUD": "Sky feature",
            "MOON": "Earth's satellite",
            "STAR": "Night sky twinkler",
            "FIRE": "Campfire element",
            "WIND": "Breeze",
            "RAIN": "Precipitation"
        }

        if answer in specific_clues:
            return specific_clues[answer]

        # Generic clues based on difficulty and word length
        if difficulty in ["Monday", "Tuesday"]:
            # Easy, straightforward clues
            return f"Common word: {answer.lower()}"
        elif difficulty in ["Wednesday", "Thursday"]:
            # Medium difficulty
            return f"{len(answer)}-letter word"
        else:
            # Hard, cryptic-style
            return f"Puzzle answer ({len(answer)} letters)"


class CrosswordScraper:
    """
    Main scraper class that coordinates different data sources
    """

    def __init__(self, config_path: str = "config.yaml"):
        self.config = load_config(config_path)
        self.scraping_config = self.config.get("scraping", {})
        self.output_dir = Path("data/raw")
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.synthetic_generator = SyntheticPuzzleGenerator()
        self.scraped_puzzles = []

    def scrape_puzzles(self, source: str = "synthetic") -> List[Dict]:
        """
        Main scraping function

        Args:
            source: Data source - "synthetic", "public_archive", or "custom"
        """
        if source == "synthetic":
            return self._scrape_synthetic()
        elif source == "public_archive":
            return self._scrape_public_archive()
        else:
            logger.error(f"Unknown source: {source}")
            return []

    def _scrape_synthetic(self) -> List[Dict]:
        """Generate synthetic puzzles for training"""
        logger.info("Generating synthetic puzzles...")

        target_count = self.scraping_config.get("target_count", 1000)
        if self.scraping_config.get("test_mode", True):
            target_count = self.scraping_config.get("test_count", 10)

        start_date = datetime.strptime(
            self.scraping_config.get("start_date", "2020-01-01"),
            "%Y-%m-%d"
        )

        puzzles = []

        for i in tqdm(range(target_count), desc="Generating puzzles"):
            # Generate puzzle for sequential dates
            puzzle_date = start_date + timedelta(days=i)
            puzzle_id = format_date_as_puzzle_id(puzzle_date, "synthetic")

            # Alternate between sizes
            size = (15, 15) if i % 3 != 0 else (21, 21)

            puzzle = self.synthetic_generator.generate_puzzle(
                puzzle_id=puzzle_id,
                date=puzzle_date,
                size=size
            )

            # Validate puzzle structure
            is_valid, errors = validate_puzzle_structure(puzzle)
            if not is_valid:
                logger.warning(f"Invalid puzzle {puzzle_id}: {errors}")
                continue

            puzzles.append(puzzle)

        logger.info(f"Generated {len(puzzles)} synthetic puzzles")
        return puzzles

    def _scrape_public_archive(self) -> List[Dict]:
        """
        Scrape from public crossword archives

        NOTE: This is a placeholder. You should:
        1. Identify public, legal crossword sources
        2. Check their robots.txt and terms of service
        3. Implement respectful scraping with delays
        4. Consider using APIs if available
        """
        logger.warning("Public archive scraping not yet implemented")
        logger.info("Consider using:")
        logger.info("  - Crossword Nexus (crosswordnexus.com)")
        logger.info("  - Open-source puzzle repositories")
        logger.info("  - APIs from puzzle providers")
        return []

    def save_puzzles(self, puzzles: List[Dict], filename: str = "puzzles.jsonl") -> None:
        """Save scraped puzzles to JSONL file"""
        output_path = self.output_dir / filename
        save_jsonl(puzzles, str(output_path))
        logger.info(f"Saved {len(puzzles)} puzzles to {output_path}")

    def load_puzzles(self, filename: str = "puzzles.jsonl") -> List[Dict]:
        """Load puzzles from JSONL file"""
        from utils import load_jsonl
        input_path = self.output_dir / filename
        if not input_path.exists():
            logger.error(f"File not found: {input_path}")
            return []
        return load_jsonl(str(input_path))

    def scrape_and_save(self, source: str = "synthetic") -> str:
        """Scrape puzzles and save to file"""
        puzzles = self.scrape_puzzles(source)

        if not puzzles:
            logger.error("No puzzles scraped")
            return ""

        filename = f"puzzles_{source}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"
        self.save_puzzles(puzzles, filename)

        # Print statistics
        self._print_statistics(puzzles)

        return filename

    def _print_statistics(self, puzzles: List[Dict]) -> None:
        """Print statistics about scraped puzzles"""
        logger.info("\n" + "="*50)
        logger.info("PUZZLE COLLECTION STATISTICS")
        logger.info("="*50)
        logger.info(f"Total puzzles: {len(puzzles)}")

        # Count by day of week
        day_counts = {}
        size_counts = {}
        for puzzle in puzzles:
            day = puzzle.get("day_of_week", "Unknown")
            day_counts[day] = day_counts.get(day, 0) + 1

            size = tuple(puzzle.get("size", []))
            size_counts[size] = size_counts.get(size, 0) + 1

        logger.info("\nPuzzles by day:")
        for day, count in sorted(day_counts.items()):
            logger.info(f"  {day}: {count}")

        logger.info("\nPuzzles by size:")
        for size, count in sorted(size_counts.items()):
            logger.info(f"  {size}: {count}")

        # Average stats
        avg_words = sum(p["stats"]["word_count"] for p in puzzles) / len(puzzles)
        logger.info(f"\nAverage word count: {avg_words:.1f}")

        logger.info("="*50 + "\n")


def main():
    """Main entry point for scraper"""
    import argparse

    parser = argparse.ArgumentParser(description="Crossword puzzle scraper")
    parser.add_argument(
        "--source",
        choices=["synthetic", "public_archive"],
        default="synthetic",
        help="Data source to scrape from"
    )
    parser.add_argument(
        "--config",
        default="config.yaml",
        help="Path to configuration file"
    )

    args = parser.parse_args()

    scraper = CrosswordScraper(config_path=args.config)
    filename = scraper.scrape_and_save(source=args.source)

    if filename:
        logger.info(f"\nSuccess! Puzzles saved to: data/raw/{filename}")
        logger.info("Next step: Run dataset_builder.py to prepare training data")


if __name__ == "__main__":
    main()
