"""
看板見積もり明細モデル
"""
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from app import db

class SignboardEstimateItem(db.Model):
    """看板見積もり明細"""
    __tablename__ = 'T_看板見積もり明細'
    
    id = Column('ID', Integer, primary_key=True, autoincrement=True)
    estimate_id = Column('見積もりID', Integer, ForeignKey('T_看板見積もり.ID'), nullable=False)
    material_id = Column('材質ID', Integer, ForeignKey('T_材質.ID'), nullable=False)
    width = Column('幅', Numeric(10, 2), nullable=False, comment='幅（mm）')
    height = Column('高さ', Numeric(10, 2), nullable=False, comment='高さ（mm）')
    quantity = Column('数量', Integer, nullable=False, default=1)
    area = Column('面積', Numeric(10, 4), comment='面積（㎡）')
    weight = Column('重量', Numeric(10, 4), comment='重量（kg）')
    price_type = Column('単価タイプ', String(20), nullable=False, comment='area: 面積単価, weight: 重量単価, volume: 体積単価')
    unit_price = Column('単価', Numeric(10, 2), nullable=False)
    discount_rate = Column('割引率', Numeric(5, 2), default=0, comment='割引率（%）')
    discounted_unit_price = Column('割引後単価', Numeric(10, 2), comment='割引後単価')
    subtotal = Column('小計', Numeric(12, 2), nullable=False, comment='小計（税抜）')
    created_at = Column('作成日時', DateTime, nullable=False)
    updated_at = Column('更新日時', DateTime, nullable=False)
    
    # リレーションシップ
    estimate = relationship('SignboardEstimate', back_populates='items')
    material = relationship('Material', backref='estimate_items')
    
    def __repr__(self):
        return f'<SignboardEstimateItem {self.id}: 見積もり{self.estimate_id} 材質{self.material_id}>'
