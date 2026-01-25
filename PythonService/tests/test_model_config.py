"""
Tests for ASR Model Configuration Management
"""

import pytest
from fastapi import status

from asr.model_config import (
    ModelManager,
    ModelSize,
    ASRModelConfig,
    ModelInfo
)


class TestModelSize:
    """Test ModelSize enum"""

    def test_all_models(self):
        """Test getting all available models"""
        models = ModelSize.all()
        assert models == ["tiny", "base", "small", "medium", "large"]

    def test_model_descriptions(self):
        """Test model descriptions"""
        tiny_desc = ModelSize.TINY.description()
        assert "fastest" in tiny_desc.lower()
        assert "39M" in tiny_desc


class TestASRModelConfig:
    """Test ASRModelConfig dataclass"""

    def test_default_config(self):
        """Test default configuration"""
        config = ASRModelConfig()
        assert config.model_size == "base"
        assert config.language is None
        assert config.fp16 is True

    def test_custom_config(self):
        """Test custom configuration"""
        config = ASRModelConfig(
            model_size="tiny",
            language="en",
            fp16=False
        )
        assert config.model_size == "tiny"
        assert config.language == "en"
        assert config.fp16 is False

    def test_invalid_model_size(self):
        """Test invalid model size raises error"""
        with pytest.raises(ValueError):
            ASRModelConfig(model_size="invalid")

    def test_valid_model_sizes(self):
        """Test all valid model sizes"""
        for size in ModelSize.all():
            config = ASRModelConfig(model_size=size)
            assert config.model_size == size


class TestModelInfo:
    """Test ModelInfo dataclass"""

    def test_get_all_models(self):
        """Test getting all model info"""
        models = ModelInfo.get_all()
        assert len(models) == 5
        assert "tiny" in models
        assert "base" in models
        assert "small" in models
        assert "medium" in models
        assert "large" in models

    def test_model_info_structure(self):
        """Test model info has required fields"""
        models = ModelInfo.get_all()

        for size, info in models.items():
            assert hasattr(info, "size")
            assert hasattr(info, "params")
            assert hasattr(info, "download_size")
            assert hasattr(info, "ram_required")
            assert hasattr(info, "speed")
            assert hasattr(info, "description")

    def test_tiny_model_info(self):
        """Test tiny model specific info"""
        models = ModelInfo.get_all()
        tiny = models["tiny"]

        assert tiny.params == "39M"
        assert "40MB" in tiny.download_size
        assert "1GB" in tiny.ram_required

    def test_base_model_info(self):
        """Test base model specific info"""
        models = ModelInfo.get_all()
        base = models["base"]

        assert base.params == "74M"
        assert "150MB" in base.download_size
        assert "1GB" in base.ram_required


class TestModelManager:
    """Test ModelManager class"""

    @pytest.fixture
    def manager(self):
        """Create a model manager instance"""
        return ModelManager()

    def test_initial_config(self, manager):
        """Test initial configuration"""
        assert manager.current_model_size == "base"
        assert manager.config.model_size == "base"
        assert manager.config.language is None
        assert manager.config.fp16 is True

    def test_set_model_size(self, manager):
        """Test setting model size"""
        manager.set_model_size("tiny")
        assert manager.current_model_size == "tiny"

    def test_set_invalid_model_size(self, manager):
        """Test setting invalid model size raises error"""
        with pytest.raises(ValueError):
            manager.set_model_size("invalid")

    def test_set_language(self, manager):
        """Test setting language"""
        manager.set_language("zh")
        assert manager.config.language == "zh"

    def test_set_fp16(self, manager):
        """Test setting fp16 mode"""
        manager.set_fp16(False)
        assert manager.config.fp16 is False

    def test_get_available_models(self, manager):
        """Test getting available models"""
        models = manager.get_available_models()
        assert len(models) == 5
        assert "tiny" in models

    def test_get_model_info(self, manager):
        """Test getting specific model info"""
        tiny_info = manager.get_model_info("tiny")
        assert tiny_info.size == "tiny"
        assert tiny_info.params == "39M"

    def test_get_invalid_model_info(self, manager):
        """Test getting info for invalid model"""
        with pytest.raises(ValueError):
            manager.get_model_info("invalid")

    def test_reset_to_defaults(self, manager):
        """Test resetting to defaults"""
        # Change config
        manager.set_model_size("tiny")
        manager.set_language("en")

        # Reset
        manager.reset_to_defaults()

        # Verify defaults restored
        assert manager.current_model_size == "base"
        assert manager.config.language is None


class TestModelConfigAPI:
    """Integration tests for model configuration API endpoints"""

    @pytest.fixture
    def client(self):
        """Create HTTP client"""
        import httpx
        return httpx.Client(base_url="http://127.0.0.1:8000")

    def test_get_config(self, client):
        """Test GET /api/asr/config endpoint"""
        response = client.get("/api/asr/config")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "current_model" in data
        assert "available_models" in data
        assert isinstance(data["available_models"], list)

    def test_list_models(self, client):
        """Test GET /api/asr/models endpoint"""
        response = client.get("/api/asr/models")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "tiny" in data
        assert "base" in data
        assert data["tiny"]["params"] == "39M"

    def test_get_model_info(self, client):
        """Test GET /api/asr/models/{size} endpoint"""
        response = client.get("/api/asr/models/tiny")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["size"] == "tiny"
        assert data["params"] == "39M"

    def test_get_invalid_model_info(self, client):
        """Test getting info for invalid model"""
        response = client.get("/api/asr/models/invalid")

        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_set_config(self, client):
        """Test POST /api/asr/config endpoint"""
        # Switch to tiny model
        response = client.post(
            "/api/asr/config",
            json={"model_size": "tiny"}
        )

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["current_model"] == "tiny"

        # Reset to base
        response = client.post("/api/asr/reset")

        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert data["current_model"] == "base"

    def test_set_invalid_config(self, client):
        """Test setting invalid configuration"""
        response = client.post(
            "/api/asr/config",
            json={"model_size": "invalid"}
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
