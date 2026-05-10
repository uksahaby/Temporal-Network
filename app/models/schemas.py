from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, ForeignKey, Boolean, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid

from app.models.database import Base


class User(Base):
    """Store user accounts"""
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    full_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sessions = relationship("NetworkSession", back_populates="user", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_user_email', 'email'),
        Index('idx_user_username', 'username'),
    )


class NetworkSession(Base):
    """Store uploaded network analysis sessions"""
    __tablename__ = "network_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    file_name = Column(String(255), nullable=False)
    file_path = Column(String(512), nullable=False)
    file_size = Column(Integer, nullable=False)
    status = Column(String(50), default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Analysis parameters
    window_size = Column(String(20), default="1h")
    step_size = Column(String(20), default="30min")
    
    # Relationships
    user = relationship("User", back_populates="sessions")
    nodes = relationship("Node", back_populates="session", cascade="all, delete-orphan")
    edges = relationship("Edge", back_populates="session", cascade="all, delete-orphan")
    analysis_results = relationship("AnalysisResult", back_populates="session", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_session_user', 'user_id'),
        Index('idx_session_status', 'status'),
        Index('idx_session_created', 'created_at'),
    )


class Node(Base):
    """Store network nodes"""
    __tablename__ = "nodes"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("network_sessions.id", ondelete="CASCADE"), nullable=False)
    node_id = Column(String(255), nullable=False)  # Original node identifier
    label = Column(String(255), nullable=True)
    attributes = Column(JSON, nullable=True)
    
    # Precomputed metrics (aggregated across all windows)
    avg_degree = Column(Float, nullable=True)
    max_degree = Column(Integer, nullable=True)
    avg_centrality = Column(Float, nullable=True)
    
    session = relationship("NetworkSession", back_populates="nodes")
    
    __table_args__ = (
        Index('idx_node_session', 'session_id'),
        Index('idx_node_id', 'session_id', 'node_id', unique=True),
    )


class Edge(Base):
    """Store network edges with temporal information"""
    __tablename__ = "edges"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("network_sessions.id", ondelete="CASCADE"), nullable=False)
    source = Column(String(255), nullable=False)
    target = Column(String(255), nullable=False)
    weight = Column(Float, default=1.0)
    timestamp = Column(DateTime, nullable=True)
    attributes = Column(JSON, nullable=True)
    
    session = relationship("NetworkSession", back_populates="edges")
    
    __table_args__ = (
        Index('idx_edge_session', 'session_id'),
        Index('idx_edge_timestamp', 'session_id', 'timestamp'),
        Index('idx_edge_source_target', 'session_id', 'source', 'target'),
    )


class AnalysisResult(Base):
    """Store analysis results and metrics for time windows"""
    __tablename__ = "analysis_results"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("network_sessions.id", ondelete="CASCADE"), nullable=False)
    window_key = Column(String(100), nullable=False)  # Window identifier
    window_start = Column(DateTime, nullable=False)
    window_end = Column(DateTime, nullable=False)
    
    # Basic metrics
    num_nodes = Column(Integer, default=0)
    num_edges = Column(Integer, default=0)
    density = Column(Float, default=0.0)
    connected_components = Column(Integer, default=0)
    giant_component_size = Column(Integer, nullable=True)
    clustering_coefficient = Column(Float, nullable=True)
    max_degree = Column(Integer, nullable=True)
    
    # Detailed metrics stored as JSON
    degree_centrality = Column(JSON, nullable=True)
    betweenness_centrality = Column(JSON, nullable=True)
    pagerank = Column(JSON, nullable=True)
    community_assignments = Column(JSON, nullable=True)
    
    # Visualization data
    nodes_data = Column(JSON, nullable=True)  # Sampled nodes for visualization
    edges_data = Column(JSON, nullable=True)  # Sampled edges for visualization
    truncated = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    session = relationship("NetworkSession", back_populates="analysis_results")
    
    __table_args__ = (
        Index('idx_result_session', 'session_id'),
        Index('idx_result_window', 'session_id', 'window_key'),
        Index('idx_result_time', 'session_id', 'window_start'),
    )


class Anomaly(Base):
    """Store detected anomalies"""
    __tablename__ = "anomalies"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("network_sessions.id", ondelete="CASCADE"), nullable=False)
    window_key = Column(String(100), nullable=False)
    anomaly_type = Column(String(50), nullable=False)  # density_anomaly, component_change, etc.
    value = Column(Float, nullable=True)
    z_score = Column(Float, nullable=True)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_anomaly_session', 'session_id'),
        Index('idx_anomaly_type', 'session_id', 'anomaly_type'),
    )


# Pydantic schemas for API request/response
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime as dt


class NetworkSessionCreate(BaseModel):
    """Schema for creating a network session"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    window_size: str = "1h"
    step_size: str = "30min"


class NetworkSessionResponse(BaseModel):
    """Schema for network session response"""
    id: str
    name: str
    description: Optional[str]
    file_name: str
    status: str
    created_at: dt
    window_size: str
    step_size: str
    
    class Config:
        from_attributes = True


class EdgeCreate(BaseModel):
    """Schema for creating an edge"""
    source: str
    target: str
    weight: float = 1.0
    timestamp: Optional[dt] = None
    attributes: Optional[Dict[str, Any]] = None


class AnalysisResultResponse(BaseModel):
    """Schema for analysis result response"""
    window_key: str
    window_start: dt
    window_end: dt
    num_nodes: int
    num_edges: int
    density: float
    connected_components: int
    clustering_coefficient: Optional[float]
    
    class Config:
        from_attributes = True


class MetricsTimelineResponse(BaseModel):
    """Schema for metrics timeline"""
    time: str
    density: float
    nodes: int
    edges: int
    components: int
    giant_component: Optional[float]
    max_degree: Optional[int]


class AnomalyResponse(BaseModel):
    """Schema for anomaly response"""
    window_key: str
    anomaly_type: str
    value: Optional[float]
    z_score: Optional[float]
    description: Optional[str]
    detected_at: dt
    
    class Config:
        from_attributes = True


class VisualizationDataResponse(BaseModel):
    """Schema for visualization data"""
    time_windows: List[Dict[str, Any]]
    metrics_timeline: List[MetricsTimelineResponse]
    summary: Dict[str, Any]
    anomalies: Optional[List[AnomalyResponse]] = []
