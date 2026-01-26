from unittest.mock import Mock
import pytest
from databarn.grain import Grain, Info, Seed
from databarn.exceptions import CobConsistencyError
from databarn.constants import UNSET

class TestInfo:
    def test_init(self):
        info = Info(a=1, b="test")
        assert info.a == 1
        assert info.b == "test"

    def test_repr(self):
        info = Info(a=1)
        assert repr(info) == "Info(a=1)"

class TestGrain:
    def test_init_defaults(self):
        grain = Grain()
        assert grain.default is None
        assert grain.pk is False
        assert grain.required is False
        assert grain.auto is False
        assert grain.frozen is False
        assert grain.unique is False
        assert grain.comparable is False
        assert grain.key == ""
        assert grain.factory is None
        assert grain.parent_model is None
        assert grain.child_model is None

    def test_init_custom(self):
        def factory(): return 1
        
        grain = Grain(default=10, pk=True, required=True)
        assert grain.default == 10
        assert grain.pk is True
        assert grain.required is True
        
        grain2 = Grain(factory=factory, key="custom_key")
        assert grain2.factory == factory
        assert grain2.key == "custom_key"
        
        # Check info
        grain3 = Grain(some_info="value")
        assert grain3.info.some_info == "value"

    def test_validation_auto_and_default(self):
        with pytest.raises(CobConsistencyError, match="cannot be both auto and have a default"):
            Grain(auto=True, default=1)

    def test_validation_default_and_factory(self):
        with pytest.raises(CobConsistencyError, match="cannot have both a default value and a factory"):
            Grain(default=1, factory=lambda: 1)

    def test_set_model_attrs(self):
        grain = Grain()
        mock_model = Mock()
        grain._set_model_attrs(mock_model, "label", int)
        assert grain.parent_model == mock_model
        assert grain.label == "label"
        assert grain.type == int

    def test_set_child_model(self):
        grain = Grain()
        mock_child = Mock()
        grain._set_child_model(mock_child, True)
        assert grain.child_model == mock_child
        assert grain.is_child_barn_ref is True

    def test_set_key(self):
        grain = Grain()
        grain.set_key("new_key")
        assert grain.key == "new_key"

    def test_repr(self):
        grain = Grain(default=1)
        # The repr output order depends on __dict__ order, which preserves insertion order in recent Python.
        # We'll just check if it contains the class name and some key attributes.
        r = repr(grain)
        assert "Grain(" in r
        assert "default=1" in r

class TestSeed:
    @pytest.fixture
    def mock_cob(self):
        return Mock()

    @pytest.fixture
    def grain(self):
        grain = Grain(default=1)
        grain.label = "score" # Simulate Dna setting label
        return grain

    def test_init_without_sentinel(self, grain, mock_cob):
        seed = Seed(grain, mock_cob, init_with_sentinel=False)
        assert seed.grain == grain
        assert seed.cob == mock_cob
        # Should not have set any value on cob yet (unless implicitly relying on something else, 
        # but the init logic only sets specific value if sentinel is True)
        
    def test_init_with_sentinel(self, grain, mock_cob):
        # We need to make sure the mock_cob allows setting attributes, 
        # but Mock() usually handles that fine.
        # However, Seed uses object.__setattr__(cob, label, value) which bypasses standard setattr?
        # No, force_set_value uses object.__setattr__(self.cob, ...).
        # Mocks might behave differently with object.__setattr__.
        # Let's use a real dummy class for Cob to be safe or ensure Mock works.
        class DummyCob:
            pass
        
        cob = DummyCob()
        seed = Seed(grain, cob, init_with_sentinel=True)
        assert getattr(cob, "score") is UNSET

    def test_get_set_value(self, grain):
        class DummyCob:
            pass
        cob = DummyCob()
        seed = Seed(grain, cob, init_with_sentinel=False)
        
        # Test set
        seed.set_value(100)
        assert cob.score == 100
        
        # Test get
        assert seed.get_value() == 100

    def test_force_set_value(self, grain):
        class DummyCob:
            def __setattr__(self, key, value):
                # This should be bypassed by force_set_value if it uses object.__setattr__
                raise Exception("Should not be called")
        
        cob = DummyCob()
        seed = Seed(grain, cob, init_with_sentinel=False)
        
        seed.force_set_value(999)
        # Check via object.__getattribute__ to verify it was set
        assert object.__getattribute__(cob, "score") == 999

    def test_has_been_set(self, grain):
        class DummyCob:
            pass
        cob = DummyCob()
        seed = Seed(grain, cob, init_with_sentinel=True)
        
        assert seed.has_been_set is False
        
        seed.set_value(10)
        assert seed.has_been_set is True

    def test_getattr_delegation(self, grain):
        class DummyCob:
            pass
        cob = DummyCob()
        grain.some_custom_attr = "hello"
        seed = Seed(grain, cob, init_with_sentinel=False)
        
        assert seed.some_custom_attr == "hello"

    def test_repr(self, grain):
        class DummyCob:
            pass
        cob = DummyCob()
        seed = Seed(grain, cob, init_with_sentinel=True)
        r = repr(seed)
        assert "Seed(" in r
        assert "score" in r # label
        assert "has_been_set=False" in r
