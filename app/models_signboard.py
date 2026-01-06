from __future__ import annotations
from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .db import Base


class Material(Base):
    """材質マスタテーブル"""
    __tablename__ = 'T_材質'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey('T_テナント.id'), nullable=False, index=True)
    name = Column(String(100), nullable=False, comment='材質名')
    
    # 単価タイプ: 'area' (面積単価) または 'weight' (重量単価)
    price_type = Column(String(20), nullable=False, default='area', comment='単価タイプ: area, weight')
    
    # 面積単価（円/㎡）- price_type='area'の場合に使用
    unit_price_area = Column(Float, nullable=True, comment='単価（円/㎡）')
    
    # 重量単価（円/kg）- price_type='weight'の場合に使用
    unit_price_weight = Column(Float, nullable=True, comment='単価（円/kg）')
    
    # 比重（kg/㎡/mm）- price_type='weight'の場合に使用
    # 例: アルミ複合板 = 約2.7 kg/㎡/mm
    specific_gravity = Column(Float, nullable=True, comment='比重（kg/㎡/mm）')
    
    # 板厚（mm）- price_type='weight'の場合に使用
    thickness = Column(Float, nullable=True, comment='板厚（mm）')
    
    description = Column(Text, comment='説明')
    active = Column(Integer, default=1, nullable=False, comment='有効フラグ')
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # リレーション
    tenant = relationship("TTenant", foreign_keys=[tenant_id])
    estimates = relationship("SignboardEstimate", back_populates="material")
    volume_discounts = relationship("MaterialVolumeDiscount", back_populates="material", order_by="MaterialVolumeDiscount.min_quantity")


class MaterialVolumeDiscount(Base):
    """材質ボリュームディスカウントテーブル"""
    __tablename__ = 'T_材質ボリュームディスカウント'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    material_id = Column(Integer, ForeignKey('T_材質.id'), nullable=False, index=True)
    
    # 数量範囲
    min_quantity = Column(Integer, nullable=False, comment='最小数量')
    max_quantity = Column(Integer, nullable=True, comment='最大数量（NULLの場合は無制限）')
    
    # 割引率（%）または割引後単価
    discount_type = Column(String(20), nullable=False, default='rate', comment='割引タイプ: rate(割引率), price(割引後単価)')
    discount_rate = Column(Float, nullable=True, comment='割引率（%）')
    discount_price = Column(Float, nullable=True, comment='割引後単価')
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # リレーション
    material = relationship("Material", back_populates="volume_discounts")


class SignboardEstimate(Base):
    """看板見積もりテーブル"""
    __tablename__ = 'T_看板見積もり'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    tenant_id = Column(Integer, ForeignKey('T_テナント.id'), nullable=False, index=True)
    store_id = Column(Integer, ForeignKey('T_店舗.id'), nullable=True, index=True)
    created_by = Column(Integer, nullable=False, comment='作成者ID')
    created_by_role = Column(String(50), nullable=False, comment='作成者ロール')
    
    # 見積もり情報
    estimate_number = Column(String(50), unique=True, nullable=False, comment='見積もり番号')
    customer_name = Column(String(200), comment='顧客名')
    
    # 看板仕様
    width = Column(Float, nullable=False, comment='幅（mm）')
    height = Column(Float, nullable=False, comment='高さ（mm）')
    material_id = Column(Integer, ForeignKey('T_材質.id'), nullable=False)
    quantity = Column(Integer, default=1, nullable=False, comment='数量')
    
    # 価格計算情報
    area = Column(Float, nullable=False, comment='面積（㎡）')
    weight = Column(Float, nullable=True, comment='重量（kg）- 重量単価の場合のみ')
    price_type = Column(String(20), nullable=False, comment='単価タイプ: area, weight')
    unit_price = Column(Float, nullable=False, comment='適用単価（割引前）')
    discount_rate = Column(Float, default=0.0, nullable=False, comment='割引率（%）')
    discounted_unit_price = Column(Float, nullable=False, comment='割引後単価')
    subtotal = Column(Float, nullable=False, comment='小計（円）')
    tax_rate = Column(Float, default=0.10, nullable=False, comment='消費税率')
    tax_amount = Column(Float, nullable=False, comment='消費税額（円）')
    total_amount = Column(Float, nullable=False, comment='合計金額（円）')
    
    # 備考
    notes = Column(Text, comment='備考')
    
    # ステータス
    status = Column(String(20), default='draft', nullable=False, comment='ステータス: draft, sent, approved, rejected')
    
    created_at = Column(DateTime, default=datetime.now, nullable=False)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now, nullable=False)
    
    # リレーションシップ
    tenant = relationship("TTenant", backref="signboard_estimates")
    material = relationship("Material", backref="signboard_estimates")
    items = relationship("SignboardEstimateItem", back_populates="estimate", cascade="all, delete-orphan")