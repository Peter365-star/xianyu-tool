export interface Product {
  id: string;
  xianyu_id: string;
  title: string;
  price: number;
  original_price: number | null;
  images: string[] | null;
  seller_name: string | null;
  seller_level: string | null;
  want_count: number;
  view_count: number;
  category: string | null;
  tags: string[] | null;
  publish_time: string | null;
  fetched_at: string;
}

export interface HotProduct extends Product {
  score: number;
  want_velocity: number;
  price_advantage: number;
  engagement_rate: number;
  days_ago: number | null;
  hotness: number | null;
}

export interface ProductSearchResult {
  items: HotProduct[];
  total: number;
  page: number;
  page_size: number;
}

export interface Category {
  id: string;
  name: string;
  icon: string;
}

export interface CategoryList {
  xianyu: Category[];
  industries: string[];
}

export interface CrawlTask {
  id: string;
  keyword: string;
  category: string | null;
  status: string;
  items_found: number;
  level: string | null;
  duration_minutes: number | null;
  products_data: { title: string; price: number; seller_name: string; link: string }[] | null;
  error: string | null;
  started_at: string | null;
  ended_at: string | null;
  created_at: string;
}

export interface LoginRequest {
  username: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}
