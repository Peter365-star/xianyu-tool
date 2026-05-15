import { Card, Tag, Typography, Space } from 'antd';
import { HeartOutlined, EyeOutlined } from '@ant-design/icons';
import type { HotProduct } from '../types';

const { Text, Paragraph } = Typography;

export default function ProductCard({ product }: { product: HotProduct }) {
  return (
    <Card
      hoverable
      style={{ marginBottom: 12 }}
      cover={
        product.images?.[0] ? (
          <img alt={product.title} src={product.images[0]} style={{ height: 180, objectFit: 'cover' }} />
        ) : (
          <div style={{ height: 180, background: '#f0f0f0', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#bbb' }}>
            暂无图片
          </div>
        )
      }
    >
      <Paragraph ellipsis={{ rows: 2 }} style={{ marginBottom: 8 }}>
        {product.title}
      </Paragraph>
      <Space size="middle" style={{ marginBottom: 8 }}>
        <Text strong style={{ color: '#ff4d4f', fontSize: 18 }}>
          ¥{product.price}
        </Text>
        {product.original_price && (
          <Text delete type="secondary">¥{product.original_price}</Text>
        )}
      </Space>
      <div>
        <Space size="small">
          <Tag color="red">{product.score.toFixed(0)}分</Tag>
          <Text type="secondary"><HeartOutlined /> {product.want_count}</Text>
          <Text type="secondary"><EyeOutlined /> {product.view_count}</Text>
        </Space>
      </div>
      {product.tags && product.tags.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {product.tags.map((tag) => <Tag key={tag}>{tag}</Tag>)}
        </div>
      )}
    </Card>
  );
}
