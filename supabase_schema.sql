-- ================================================================
--  COMPLETE SUPABASE SCHEMA — PRICE SCRAPER
--  Single file. Paste into Supabase SQL Editor and run once.
--
--  TABLES:
--    categories, pages, products, price_history,
--    users, user_interests, user_saved_products, offers
--
--  NOT INCLUDED:  admin_users  (kept separate, no relations)
--
--  YOUR ONLY INPUTS PER PRODUCT:  link  +  page_slug
-- ================================================================


-- ================================================================
--  CLEANUP  (safe to re-run — drops everything and rebuilds)
-- ================================================================
DROP TABLE IF EXISTS offers               CASCADE;
DROP TABLE IF EXISTS user_saved_products  CASCADE;
DROP TABLE IF EXISTS user_interests       CASCADE;
DROP TABLE IF EXISTS users                CASCADE;
DROP TABLE IF EXISTS price_history        CASCADE;
DROP TABLE IF EXISTS products             CASCADE;
DROP TABLE IF EXISTS pages                CASCADE;
DROP TABLE IF EXISTS categories           CASCADE;

DROP FUNCTION IF EXISTS add_product(text, text);
DROP FUNCTION IF EXISTS fn_set_updated_at();
DROP FUNCTION IF EXISTS fn_log_price_history();
DROP FUNCTION IF EXISTS fn_create_user_profile();
DROP FUNCTION IF EXISTS fn_deactivate_expired_offers();
DROP FUNCTION IF EXISTS get_best_offers(int);
DROP FUNCTION IF EXISTS get_page_offers(text, int);
DROP FUNCTION IF EXISTS get_page_by_price(text, int);
DROP FUNCTION IF EXISTS get_price_trend(uuid);
DROP FUNCTION IF EXISTS get_stale_products(int);
DROP FUNCTION IF EXISTS add_interest(uuid, uuid, uuid);
DROP FUNCTION IF EXISTS remove_interest(uuid, uuid);
DROP FUNCTION IF EXISTS save_product(uuid, uuid);
DROP FUNCTION IF EXISTS unsave_product(uuid, uuid);
DROP FUNCTION IF EXISTS get_user_wishlist(uuid);
DROP FUNCTION IF EXISTS get_personalized_feed(uuid, int);
DROP FUNCTION IF EXISTS get_active_offers(int);
DROP FUNCTION IF EXISTS get_offers_for_user(uuid, int);


-- ================================================================
--  1. CATEGORIES
--     Top-level groups.  e.g. "Footwear", "Fashion", "Electronics"
-- ================================================================
CREATE TABLE categories (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  name        TEXT        NOT NULL UNIQUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE  categories      IS 'Top-level groupings. e.g. Footwear, Fashion, Electronics.';
COMMENT ON COLUMN categories.name IS 'Human-readable label shown in the UI.';


-- ================================================================
--  2. PAGES  (subcategory / scrape target)
--     e.g. name="Killer Shoes"  slug="killer_shoes"
--     slug is YOUR INPUT #2 when adding a product.
-- ================================================================
CREATE TABLE pages (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  category_id  UUID        NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
  name         TEXT        NOT NULL,
  slug         TEXT        NOT NULL UNIQUE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_pages_category_id ON pages(category_id);
CREATE INDEX idx_pages_slug        ON pages(slug);

COMMENT ON TABLE  pages      IS 'Subcategory pages. Each belongs to one category.';
COMMENT ON COLUMN pages.slug IS 'URL-safe key. This is YOUR INPUT #2 when adding products.';


-- ================================================================
--  3. PRODUCTS
--     YOU insert:   link + page_slug  (via add_product function)
--     SCRAPER sets: name, description, image_url, price, etc.
--     discount_pct: computed automatically — never set manually.
-- ================================================================
CREATE TABLE products (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  page_id           UUID        NOT NULL REFERENCES pages(id) ON DELETE CASCADE,

  -- ── YOUR INPUT #1 ─────────────────────────────────────────────
  link              TEXT        NOT NULL UNIQUE,

  -- ── SCRAPED FIELDS ────────────────────────────────────────────
  name              TEXT,
  description       TEXT,
  image_url         TEXT,
  price             NUMERIC(12,2),
  discounted_price  NUMERIC(12,2),

  -- ── AUTO-COMPUTED ─────────────────────────────────────────────
  discount_pct      NUMERIC(5,2) GENERATED ALWAYS AS (
    CASE
      WHEN price IS NOT NULL
       AND price > 0
       AND discounted_price IS NOT NULL
       AND discounted_price < price
      THEN ROUND(((price - discounted_price) / price) * 100, 2)
      ELSE 0
    END
  ) STORED,

  -- ── SCRAPER STATE ─────────────────────────────────────────────
  scrape_status     TEXT        NOT NULL DEFAULT 'pending'
                    CHECK (scrape_status IN ('pending','success','failed')),
  last_checked      TIMESTAMPTZ,
  created_at        TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at        TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_products_page_id        ON products(page_id);
CREATE INDEX idx_products_discount_pct   ON products(discount_pct DESC);
CREATE INDEX idx_products_price          ON products(discounted_price ASC NULLS LAST);
CREATE INDEX idx_products_scrape_status  ON products(scrape_status);
CREATE INDEX idx_products_last_checked   ON products(last_checked ASC NULLS FIRST);

COMMENT ON TABLE  products              IS 'One row per scraped product. Only link+page_id required at insert.';
COMMENT ON COLUMN products.link         IS 'YOUR INPUT #1. Unique. Scraper uses this URL.';
COMMENT ON COLUMN products.discount_pct IS 'Auto-computed from price and discounted_price. Never set manually.';


-- ================================================================
--  4. PRICE HISTORY
--     Written automatically by trigger on every price change.
--     Never insert manually.
-- ================================================================
CREATE TABLE price_history (
  id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id        UUID        NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  price             NUMERIC(12,2),
  discounted_price  NUMERIC(12,2),
  recorded_at       TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_ph_product_id  ON price_history(product_id);
CREATE INDEX idx_ph_recorded_at ON price_history(recorded_at DESC);

COMMENT ON TABLE price_history IS 'Immutable price log. One row auto-inserted every time price changes.';


-- ================================================================
--  5. USERS  (public profile — mirrors Supabase auth.users)
--     Created automatically on signup via trigger.
--     Never insert manually.
-- ================================================================
CREATE TABLE users (
  id          UUID        PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email       TEXT        NOT NULL,
  full_name   TEXT,
  avatar_url  TEXT,
  is_active   BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_users_email ON users(email);

COMMENT ON TABLE  users           IS 'Public profiles. Auto-created from auth.users on signup.';
COMMENT ON COLUMN users.id        IS 'Same UUID as auth.users.id — one-to-one.';
COMMENT ON COLUMN users.is_active IS 'Set false to soft-ban without deleting the auth record.';


-- ================================================================
--  6. USER INTERESTS
--     One row = user follows a category OR a page (or both).
--     Drives the personalized feed and targeted offer alerts.
-- ================================================================
CREATE TABLE user_interests (
  id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id      UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  category_id  UUID        REFERENCES categories(id) ON DELETE CASCADE,
  page_id      UUID        REFERENCES pages(id) ON DELETE CASCADE,
  created_at   TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_interest_target
    CHECK (category_id IS NOT NULL OR page_id IS NOT NULL),

  UNIQUE (user_id, category_id, page_id)
);

CREATE INDEX idx_ui_user_id     ON user_interests(user_id);
CREATE INDEX idx_ui_category_id ON user_interests(category_id);
CREATE INDEX idx_ui_page_id     ON user_interests(page_id);

COMMENT ON TABLE user_interests IS 'Each row = user follows a category or page. Powers personalized feed.';


-- ================================================================
--  7. USER SAVED PRODUCTS  (wishlist / bookmarks)
--     Also used for price-drop notifications.
-- ================================================================
CREATE TABLE user_saved_products (
  id          UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id     UUID        NOT NULL REFERENCES users(id) ON DELETE CASCADE,
  product_id  UUID        NOT NULL REFERENCES products(id) ON DELETE CASCADE,
  saved_at    TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  UNIQUE (user_id, product_id)
);

CREATE INDEX idx_usp_user_id    ON user_saved_products(user_id);
CREATE INDEX idx_usp_product_id ON user_saved_products(product_id);

COMMENT ON TABLE user_saved_products IS 'Wishlist. One row per saved product per user.';


-- ================================================================
--  8. OFFERS
--     Created by admins (via your backend/API — no DB relation).
--     Attached to a product. Auto-expires when ends_at passes.
--
--     offer_type:
--       'percentage' — extra X% off on top of scraped discount
--       'flat'       — flat ₹X off
--       'coupon'     — show a coupon code at checkout
--       'bogo'       — buy one get one (label, logic in frontend)
-- ================================================================
CREATE TABLE offers (
  id              UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id      UUID        NOT NULL REFERENCES products(id) ON DELETE CASCADE,

  title           TEXT        NOT NULL,
  offer_type      TEXT        NOT NULL
                  CHECK (offer_type IN ('percentage','flat','coupon','bogo')),

  coupon_code     TEXT,
  extra_discount  NUMERIC(10,2),

  starts_at       TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  ends_at         TIMESTAMPTZ,
  is_active       BOOLEAN     NOT NULL DEFAULT TRUE,
  created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),

  CONSTRAINT chk_coupon_has_code
    CHECK (offer_type != 'coupon' OR coupon_code IS NOT NULL),

  CONSTRAINT chk_discount_has_value
    CHECK (offer_type NOT IN ('percentage','flat') OR extra_discount IS NOT NULL)
);

CREATE INDEX idx_offers_product_id ON offers(product_id);
CREATE INDEX idx_offers_is_active  ON offers(is_active) WHERE is_active = TRUE;
CREATE INDEX idx_offers_ends_at    ON offers(ends_at);

COMMENT ON TABLE  offers             IS 'Admin deals stacked on top of scraped prices. No relation to admin_users.';
COMMENT ON COLUMN offers.ends_at     IS 'NULL = never expires. Trigger auto-sets is_active=false when this passes.';
COMMENT ON COLUMN offers.coupon_code IS 'Required when offer_type = coupon.';


-- ================================================================
--  TRIGGERS
-- ================================================================

-- ── Auto-refresh products.updated_at ────────────────────────────
CREATE OR REPLACE FUNCTION fn_set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_products_updated_at
  BEFORE UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION fn_set_updated_at();


-- ── Auto-log price history on every price change ─────────────────
CREATE OR REPLACE FUNCTION fn_log_price_history()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF (TG_OP = 'INSERT')
  OR (OLD.price            IS DISTINCT FROM NEW.price)
  OR (OLD.discounted_price IS DISTINCT FROM NEW.discounted_price)
  THEN
    INSERT INTO price_history (product_id, price, discounted_price)
    VALUES (NEW.id, NEW.price, NEW.discounted_price);
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_products_price_history
  AFTER INSERT OR UPDATE ON products
  FOR EACH ROW EXECUTE FUNCTION fn_log_price_history();


-- ── Auto-create user profile on Supabase signup ──────────────────
CREATE OR REPLACE FUNCTION fn_create_user_profile()
RETURNS TRIGGER LANGUAGE plpgsql SECURITY DEFINER AS $$
BEGIN
  INSERT INTO users (id, email, full_name, avatar_url)
  VALUES (
    NEW.id,
    NEW.email,
    NEW.raw_user_meta_data->>'full_name',
    NEW.raw_user_meta_data->>'avatar_url'
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN NEW;
END;
$$;

CREATE OR REPLACE TRIGGER trg_create_user_profile
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION fn_create_user_profile();


-- ── Auto-deactivate expired offers ───────────────────────────────
CREATE OR REPLACE FUNCTION fn_deactivate_expired_offers()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.ends_at IS NOT NULL AND NEW.ends_at < NOW() THEN
    NEW.is_active = FALSE;
  END IF;
  RETURN NEW;
END;
$$;

CREATE TRIGGER trg_offers_expiry
  BEFORE INSERT OR UPDATE ON offers
  FOR EACH ROW EXECUTE FUNCTION fn_deactivate_expired_offers();

-- Optional: bulk-expire via pg_cron every 15 min
-- (enable pg_cron extension in Supabase Dashboard → Extensions first)
--
-- SELECT cron.schedule('expire-offers', '*/15 * * * *', $$
--   UPDATE offers SET is_active = FALSE
--   WHERE is_active = TRUE AND ends_at IS NOT NULL AND ends_at < NOW();
-- $$);


-- ================================================================
--  FUNCTIONS
-- ================================================================

-- ----------------------------------------------------------------
--  PRODUCTS
-- ----------------------------------------------------------------

-- add_product
-- Your only insert call. Pass link + page_slug.
-- Returns: new product UUID, or NULL if link already exists.
--
-- SELECT add_product('https://myntra.com/shoe-123', 'killer_shoes');
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION add_product(
  p_link       TEXT,
  p_page_slug  TEXT
)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE
  v_page_id UUID;
  v_id      UUID;
BEGIN
  SELECT id INTO v_page_id FROM pages WHERE slug = p_page_slug;
  IF v_page_id IS NULL THEN
    RAISE EXCEPTION 'Page slug "%" does not exist. Create it first.', p_page_slug;
  END IF;
  INSERT INTO products (link, page_id)
  VALUES (p_link, v_page_id)
  ON CONFLICT (link) DO NOTHING
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;


-- get_best_offers
-- Top N products globally sorted by highest discount %.
-- Powers homepage "Best Deals" / offer banners.
--
-- SELECT * FROM get_best_offers(20);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_best_offers(p_limit INT DEFAULT 20)
RETURNS TABLE (
  product_id        UUID,
  name              TEXT,
  image_url         TEXT,
  link              TEXT,
  price             NUMERIC,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC,
  page_name         TEXT,
  page_slug         TEXT,
  category_name     TEXT
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    p.id, p.name, p.image_url, p.link,
    p.price, p.discounted_price, p.discount_pct,
    pg.name, pg.slug, c.name
  FROM products    p
  JOIN pages       pg ON p.page_id      = pg.id
  JOIN categories  c  ON pg.category_id = c.id
  WHERE p.scrape_status = 'success' AND p.discount_pct > 0
  ORDER BY p.discount_pct DESC
  LIMIT p_limit;
$$;


-- get_page_offers
-- Top offers inside one page, sorted by discount %.
--
-- SELECT * FROM get_page_offers('shoes_under_1000', 20);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_page_offers(
  p_page_slug TEXT,
  p_limit     INT DEFAULT 20
)
RETURNS TABLE (
  product_id        UUID,
  name              TEXT,
  image_url         TEXT,
  link              TEXT,
  price             NUMERIC,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    p.id, p.name, p.image_url, p.link,
    p.price, p.discounted_price, p.discount_pct
  FROM products  p
  JOIN pages     pg ON p.page_id = pg.id
  WHERE pg.slug = p_page_slug
    AND p.scrape_status = 'success'
    AND p.discount_pct  > 0
  ORDER BY p.discount_pct DESC
  LIMIT p_limit;
$$;


-- get_page_by_price
-- Products in a page sorted cheapest first.
--
-- SELECT * FROM get_page_by_price('killer_shoes', 50);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_page_by_price(
  p_page_slug TEXT,
  p_limit     INT DEFAULT 50
)
RETURNS TABLE (
  product_id        UUID,
  name              TEXT,
  image_url         TEXT,
  link              TEXT,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    p.id, p.name, p.image_url, p.link,
    p.discounted_price, p.discount_pct
  FROM products  p
  JOIN pages     pg ON p.page_id = pg.id
  WHERE pg.slug = p_page_slug
    AND p.scrape_status = 'success'
  ORDER BY p.discounted_price ASC NULLS LAST
  LIMIT p_limit;
$$;


-- get_price_trend
-- Full price history for one product, oldest first.
-- Feed directly to a chart (Recharts, Chart.js, etc.)
--
-- SELECT * FROM get_price_trend('product-uuid');
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_price_trend(p_product_id UUID)
RETURNS TABLE (
  recorded_at       TIMESTAMPTZ,
  price             NUMERIC,
  discounted_price  NUMERIC
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT recorded_at, price, discounted_price
  FROM price_history
  WHERE product_id = p_product_id
  ORDER BY recorded_at ASC;
$$;


-- get_stale_products
-- Products never scraped or not checked in 24 h.
-- Feed this to your scraper queue / Edge Function cron.
--
-- SELECT * FROM get_stale_products(100);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_stale_products(p_limit INT DEFAULT 100)
RETURNS TABLE (
  product_id UUID,
  link       TEXT,
  page_slug  TEXT
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT p.id, p.link, pg.slug
  FROM products  p
  JOIN pages     pg ON p.page_id = pg.id
  WHERE p.scrape_status = 'pending'
     OR p.last_checked  < NOW() - INTERVAL '24 hours'
  ORDER BY p.last_checked ASC NULLS FIRST
  LIMIT p_limit;
$$;


-- ----------------------------------------------------------------
--  USERS & INTERESTS
-- ----------------------------------------------------------------

-- add_interest
-- User follows a category or a page (pass NULL for whichever not needed).
--
-- SELECT add_interest('user-uuid', 'cat-uuid', NULL);   -- follow category
-- SELECT add_interest('user-uuid', NULL, 'page-uuid');  -- follow page
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION add_interest(
  p_user_id      UUID,
  p_category_id  UUID DEFAULT NULL,
  p_page_id      UUID DEFAULT NULL
)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_id UUID;
BEGIN
  INSERT INTO user_interests (user_id, category_id, page_id)
  VALUES (p_user_id, p_category_id, p_page_id)
  ON CONFLICT (user_id, category_id, page_id) DO NOTHING
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;


-- remove_interest
--
-- SELECT remove_interest('user-uuid', 'interest-uuid');
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION remove_interest(
  p_user_id     UUID,
  p_interest_id UUID
)
RETURNS VOID LANGUAGE sql SECURITY DEFINER AS $$
  DELETE FROM user_interests
  WHERE id = p_interest_id AND user_id = p_user_id;
$$;


-- ----------------------------------------------------------------
--  WISHLIST
-- ----------------------------------------------------------------

-- save_product   — safe to call twice, no duplicate error
--
-- SELECT save_product('user-uuid', 'product-uuid');
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION save_product(
  p_user_id    UUID,
  p_product_id UUID
)
RETURNS UUID LANGUAGE plpgsql SECURITY DEFINER AS $$
DECLARE v_id UUID;
BEGIN
  INSERT INTO user_saved_products (user_id, product_id)
  VALUES (p_user_id, p_product_id)
  ON CONFLICT (user_id, product_id) DO NOTHING
  RETURNING id INTO v_id;
  RETURN v_id;
END;
$$;


-- unsave_product
--
-- SELECT unsave_product('user-uuid', 'product-uuid');
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION unsave_product(
  p_user_id    UUID,
  p_product_id UUID
)
RETURNS VOID LANGUAGE sql SECURITY DEFINER AS $$
  DELETE FROM user_saved_products
  WHERE user_id = p_user_id AND product_id = p_product_id;
$$;


-- get_user_wishlist
-- All saved products for a user, newest first.
-- Includes active offer info if any exists on the product.
--
-- SELECT * FROM get_user_wishlist('user-uuid');
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_user_wishlist(p_user_id UUID)
RETURNS TABLE (
  product_id        UUID,
  name              TEXT,
  image_url         TEXT,
  link              TEXT,
  price             NUMERIC,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC,
  offer_title       TEXT,
  offer_type        TEXT,
  coupon_code       TEXT,
  saved_at          TIMESTAMPTZ
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    p.id, p.name, p.image_url, p.link,
    p.price, p.discounted_price, p.discount_pct,
    o.title, o.offer_type, o.coupon_code,
    usp.saved_at
  FROM user_saved_products usp
  JOIN products p ON usp.product_id = p.id
  LEFT JOIN LATERAL (
    SELECT title, offer_type, coupon_code
    FROM offers
    WHERE product_id = p.id AND is_active = TRUE
    ORDER BY created_at DESC
    LIMIT 1
  ) o ON TRUE
  WHERE usp.user_id = p_user_id
  ORDER BY usp.saved_at DESC;
$$;


-- ----------------------------------------------------------------
--  OFFERS
-- ----------------------------------------------------------------

-- get_active_offers
-- All currently live offers, richest discount first.
-- Powers your Offers page and homepage banners.
--
-- SELECT * FROM get_active_offers(20);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_active_offers(p_limit INT DEFAULT 20)
RETURNS TABLE (
  offer_id          UUID,
  offer_title       TEXT,
  offer_type        TEXT,
  coupon_code       TEXT,
  extra_discount    NUMERIC,
  ends_at           TIMESTAMPTZ,
  product_id        UUID,
  product_name      TEXT,
  image_url         TEXT,
  link              TEXT,
  price             NUMERIC,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC,
  page_name         TEXT,
  category_name     TEXT
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT
    o.id, o.title, o.offer_type, o.coupon_code,
    o.extra_discount, o.ends_at,
    p.id, p.name, p.image_url, p.link,
    p.price, p.discounted_price, p.discount_pct,
    pg.name, c.name
  FROM offers      o
  JOIN products    p  ON o.product_id    = p.id
  JOIN pages       pg ON p.page_id       = pg.id
  JOIN categories  c  ON pg.category_id  = c.id
  WHERE o.is_active     = TRUE
    AND p.scrape_status = 'success'
    AND (o.ends_at IS NULL OR o.ends_at > NOW())
  ORDER BY p.discount_pct DESC, o.created_at DESC
  LIMIT p_limit;
$$;


-- get_offers_for_user
-- Active offers filtered to only pages/categories the user follows.
-- Powers personalised offer notifications and alerts.
--
-- SELECT * FROM get_offers_for_user('user-uuid', 10);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_offers_for_user(
  p_user_id UUID,
  p_limit   INT DEFAULT 10
)
RETURNS TABLE (
  offer_id          UUID,
  offer_title       TEXT,
  offer_type        TEXT,
  coupon_code       TEXT,
  extra_discount    NUMERIC,
  ends_at           TIMESTAMPTZ,
  product_id        UUID,
  product_name      TEXT,
  image_url         TEXT,
  link              TEXT,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC,
  category_name     TEXT,
  page_name         TEXT
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT DISTINCT ON (o.id)
    o.id, o.title, o.offer_type, o.coupon_code,
    o.extra_discount, o.ends_at,
    p.id, p.name, p.image_url, p.link,
    p.discounted_price, p.discount_pct,
    c.name, pg.name
  FROM user_interests ui
  JOIN pages      pg ON (ui.page_id = pg.id) OR (ui.category_id = pg.category_id)
  JOIN categories c  ON pg.category_id = c.id
  JOIN products   p  ON p.page_id      = pg.id
  JOIN offers     o  ON o.product_id   = p.id
  WHERE ui.user_id      = p_user_id
    AND o.is_active     = TRUE
    AND p.scrape_status = 'success'
    AND (o.ends_at IS NULL OR o.ends_at > NOW())
  ORDER BY o.id, p.discount_pct DESC
  LIMIT p_limit;
$$;


-- get_personalized_feed
-- Products from pages/categories the user follows,
-- sorted by discount % desc. Powers the "For You" section.
--
-- SELECT * FROM get_personalized_feed('user-uuid', 30);
-- ----------------------------------------------------------------
CREATE OR REPLACE FUNCTION get_personalized_feed(
  p_user_id UUID,
  p_limit   INT DEFAULT 30
)
RETURNS TABLE (
  product_id        UUID,
  name              TEXT,
  image_url         TEXT,
  link              TEXT,
  price             NUMERIC,
  discounted_price  NUMERIC,
  discount_pct      NUMERIC,
  page_name         TEXT,
  category_name     TEXT,
  has_offer         BOOLEAN
) LANGUAGE sql STABLE SECURITY DEFINER AS $$
  SELECT DISTINCT ON (p.id)
    p.id, p.name, p.image_url, p.link,
    p.price, p.discounted_price, p.discount_pct,
    pg.name, c.name,
    EXISTS (
      SELECT 1 FROM offers o
      WHERE o.product_id = p.id AND o.is_active = TRUE
    )
  FROM user_interests ui
  JOIN pages       pg ON (ui.page_id = pg.id) OR (ui.category_id = pg.category_id)
  JOIN categories  c  ON pg.category_id = c.id
  JOIN products    p  ON p.page_id      = pg.id
  WHERE ui.user_id      = p_user_id
    AND p.scrape_status = 'success'
  ORDER BY p.id, p.discount_pct DESC
  LIMIT p_limit;
$$;


-- ================================================================
--  ROW LEVEL SECURITY (RLS)
-- ================================================================

ALTER TABLE categories           ENABLE ROW LEVEL SECURITY;
ALTER TABLE pages                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE products              ENABLE ROW LEVEL SECURITY;
ALTER TABLE price_history         ENABLE ROW LEVEL SECURITY;
ALTER TABLE users                 ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_interests        ENABLE ROW LEVEL SECURITY;
ALTER TABLE user_saved_products   ENABLE ROW LEVEL SECURITY;
ALTER TABLE offers                ENABLE ROW LEVEL SECURITY;

-- ── Public read ──────────────────────────────────────────────────
CREATE POLICY "Public read categories"    ON categories    FOR SELECT USING (TRUE);
CREATE POLICY "Public read pages"         ON pages          FOR SELECT USING (TRUE);
CREATE POLICY "Public read products"      ON products       FOR SELECT USING (TRUE);
CREATE POLICY "Public read price_history" ON price_history  FOR SELECT USING (TRUE);
CREATE POLICY "Public read active offers" ON offers         FOR SELECT USING (is_active = TRUE);

-- ── Users: own profile only ──────────────────────────────────────
CREATE POLICY "User reads own profile"    ON users FOR SELECT USING (auth.uid() = id);
CREATE POLICY "User updates own profile"  ON users FOR UPDATE USING (auth.uid() = id);

-- ── User interests: own rows only ────────────────────────────────
CREATE POLICY "User manages own interests"
  ON user_interests FOR ALL USING (auth.uid() = user_id);

-- ── Saved products: own rows only ────────────────────────────────
CREATE POLICY "User manages own saved products"
  ON user_saved_products FOR ALL USING (auth.uid() = user_id);

-- ── Service role: full access to everything ──────────────────────
CREATE POLICY "Service role all categories"   ON categories          FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all pages"        ON pages               FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all products"     ON products            FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all price_hist"   ON price_history       FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all users"        ON users               FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all interests"    ON user_interests      FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all saved"        ON user_saved_products FOR ALL USING (auth.role() = 'service_role');
CREATE POLICY "Service role all offers"       ON offers              FOR ALL USING (auth.role() = 'service_role');


-- ================================================================
--  REALTIME
-- ================================================================
ALTER PUBLICATION supabase_realtime ADD TABLE products;
ALTER PUBLICATION supabase_realtime ADD TABLE price_history;
ALTER PUBLICATION supabase_realtime ADD TABLE offers;
ALTER PUBLICATION supabase_realtime ADD TABLE user_saved_products;


-- ================================================================
--  SEED DATA
-- ================================================================
INSERT INTO categories (name) VALUES
  ('Footwear'), ('Fashion'), ('Electronics'), ('Home & Kitchen')
ON CONFLICT (name) DO NOTHING;

INSERT INTO pages (category_id, name, slug) VALUES
  ((SELECT id FROM categories WHERE name = 'Footwear'), 'Killer Shoes',       'killer_shoes'),
  ((SELECT id FROM categories WHERE name = 'Footwear'), 'Shoes Under 1000',   'shoes_under_1000'),
  ((SELECT id FROM categories WHERE name = 'Footwear'), 'Sneakers',           'sneakers'),
  ((SELECT id FROM categories WHERE name = 'Fashion'),  'Men''s Clothing',    'mens_clothing'),
  ((SELECT id FROM categories WHERE name = 'Fashion'),  'Women''s Clothing',  'womens_clothing'),
  ((SELECT id FROM categories WHERE name = 'Fashion'),  'Best Deals Today',   'best_deals_today'),
  ((SELECT id FROM categories WHERE name = 'Electronics'), 'Mobiles',         'mobiles'),
  ((SELECT id FROM categories WHERE name = 'Electronics'), 'Laptops',         'laptops')
ON CONFLICT (slug) DO NOTHING;


-- ================================================================
--  COMPLETE FUNCTION REFERENCE
-- ================================================================
--
--  PRODUCT INPUTS (your 2 inputs only)
--    add_product(link, page_slug)                → uuid
--
--  PRODUCT QUERIES
--    get_best_offers(limit)                       → table
--    get_page_offers(page_slug, limit)            → table
--    get_page_by_price(page_slug, limit)          → table
--    get_price_trend(product_id)                  → table
--    get_stale_products(limit)                    → table   ← scraper queue
--
--  USER INTERESTS
--    add_interest(user_id, category_id, page_id) → uuid
--    remove_interest(user_id, interest_id)        → void
--
--  WISHLIST
--    save_product(user_id, product_id)            → uuid
--    unsave_product(user_id, product_id)          → void
--    get_user_wishlist(user_id)                   → table
--
--  OFFERS
--    get_active_offers(limit)                     → table   ← offers page
--    get_offers_for_user(user_id, limit)          → table   ← notifications
--
--  FEED
--    get_personalized_feed(user_id, limit)        → table   ← "For You"
--
--  AUTO (no call needed)
--    fn_create_user_profile()     fires on auth.users INSERT
--    fn_log_price_history()       fires on products INSERT/UPDATE
--    fn_set_updated_at()          fires on products UPDATE
--    fn_deactivate_expired_offers() fires on offers INSERT/UPDATE
-- ================================================================
-- Enable necessary extensions

CREATE TABLE public.admin_users (
  id uuid NOT NULL DEFAULT gen_random_uuid(),
  username text UNIQUE,               -- e.g. kart123
  email text NOT NULL UNIQUE,
  hashed_password text NOT NULL,
  full_name text,
  designation text,                   -- e.g. CEO
  role text DEFAULT 'editor'::text,   -- superadmin, editor
  is_active boolean DEFAULT true,
  created_at timestamp with time zone DEFAULT timezone('utc'::text, now()),
  CONSTRAINT admin_users_pkey PRIMARY KEY (id)
);

-- --- INITIAL CEO ACCOUNT ---
-- Insert Karthik as Superadmin
INSERT INTO public.admin_users (username, email, hashed_password, full_name, designation, role)
VALUES (
    'kart123', 
    'uggekarthik96@gmail.com', 
    '$2b$12$89J0EPIhpnQrwAXU3sFyOOrna3R4ROzV3wKvUZUtrxfQFO77GzuFa', -- Hashed Karthik@123
    'karthik', 
    'ceo', 
    'superadmin'
) ON CONFLICT (email) DO NOTHING;