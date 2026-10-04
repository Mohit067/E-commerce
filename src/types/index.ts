export interface Category {
  id: string;
  name: string;
  slug: string;
  description?: string;
  image_url?: string;
  parent_id?: string | null;
  product_count?: number;
}

export interface Product {
  id: string;
  name: string;
  slug: string;
  description: string;
  category?: Category | null;
  brand?: { id: string; name: string; slug: string } | null;
  category_id?: string | null;
  brand_id?: string | null;
  price: number;
  compare_at_price: number;
  discount_pct: number;
  currency: string;
  rating_avg: number;
  rating_count: number;
  sold_count: number;
  is_featured: boolean;
  stock: number;
  images: { id: string; url: string; alt: string; position: number }[];
  variants: { id: string; sku: string; name: string; color: string; size: string; price_override: number | null; stock: number }[];
}

export interface PageRes<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

export interface OrderItem {
  id: string;
  product_name: string;
  quantity: number;
  unit_price: number;
  total_price: number;
}

export interface Order {
  id: string;
  order_number: string;
  status: string;
  total: number;
  payment_status: string;
  created_at: string;
  items: OrderItem[];
  tracking_number: string;
}
