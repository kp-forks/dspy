import dspy
from dspy.primitives.module import Module, set_attribute_by_name  # Adjust the import based on your file structure
from dspy.utils import DummyLM


class HopModule(dspy.Module):
    def __init__(self):
        super().__init__()
        self.predict1 = dspy.Predict("question -> query")
        self.predict2 = dspy.Predict("query -> answer")

    def forward(self, question):
        query = self.predict1(question=question).query
        return self.predict2(query=query)


def test_module_initialization():
    module = Module()
    assert module._compiled is False, "Module _compiled attribute should be False upon initialization"


def test_named_predictors():
    module = HopModule()
    named_preds = module.named_predictors()
    assert len(named_preds) == 2, "Should identify correct number of Predict instances"
    names, preds = zip(*named_preds, strict=False)
    assert "predict1" in names and "predict2" in names, "Named predictors should include 'predict1' and 'predict2'"


def test_predictors():
    module = HopModule()
    preds = module.predictors()
    assert len(preds) == 2, "Should return correct number of Predict instances"
    assert all(isinstance(p, dspy.Predict) for p in preds), "All returned items should be instances of PredictMock"


def test_forward():
    program = HopModule()
    dspy.settings.configure(
        lm=DummyLM(
            {
                "What is 1+1?": {"query": "let me check"},
                "let me check": {"answer": "2"},
            }
        )
    )
    result = program(question="What is 1+1?").answer
    assert result == "2"


def test_nested_named_predictors():
    class Hop2Module(dspy.Module):
        def __init__(self):
            super().__init__()
            self.hop = HopModule()

    module = Hop2Module()
    named_preds = module.named_predictors()
    assert len(named_preds) == 2
    names, _preds = zip(*named_preds, strict=False)
    assert "hop.predict1" in names
    assert "hop.predict2" in names


def test_empty_module():
    module = Module()
    assert list(module.named_sub_modules()) == [("self", module)]


def test_single_level():
    module = Module()
    module.sub = Module()
    expected = [("self", module), ("self.sub", module.sub)]
    assert list(module.named_sub_modules()) == expected


def test_multiple_levels():
    module = Module()
    module.sub = Module()
    module.sub.subsub = Module()
    expected = [("self", module), ("self.sub", module.sub), ("self.sub.subsub", module.sub.subsub)]
    assert list(module.named_sub_modules()) == expected


def test_multiple_sub_modules():
    module = Module()
    module.sub1 = Module()
    module.sub2 = Module()
    expected = [("self", module), ("self.sub1", module.sub1), ("self.sub2", module.sub2)]
    assert sorted(module.named_sub_modules()) == sorted(expected)


def test_non_base_module_attributes():
    module = Module()
    module.sub = Module()
    module.not_a_sub = "Not a self"
    expected = [("self", module), ("self.sub", module.sub)]
    assert list(module.named_sub_modules()) == expected


def test_complex_module_traversal():
    root = Module()
    root.sub_module = Module()
    root.sub_module.nested_list = [Module(), {"key": Module()}]
    root.sub_module.nested_tuple = (Module(), [Module(), Module()])
    expected_names = {
        "self",
        "self.sub_module",
        "self.sub_module.nested_list[0]",
        "self.sub_module.nested_list[1][key]",
        "self.sub_module.nested_tuple[0]",
        "self.sub_module.nested_tuple[1][0]",
        "self.sub_module.nested_tuple[1][1]",
    }
    found_names = {name for name, _ in root.named_sub_modules()}

    assert (
        found_names == expected_names
    ), f"Missing or extra modules found. Missing: {expected_names-found_names}, Extra: {found_names-expected_names}"


def test_complex_module_traversal_with_same_module():
    root = Module()
    root.sub_module = Module()
    root.sub_module.nested_list = [Module(), {"key": Module()}]
    same_module = Module()
    root.sub_module.nested_tuple = (Module(), [same_module, same_module])
    expected_names = {
        "self",
        "self.sub_module",
        "self.sub_module.nested_list[0]",
        "self.sub_module.nested_list[1][key]",  # NOTE: named_sub_modules allows recursive structures
        "self.sub_module.nested_tuple[0]",
        "self.sub_module.nested_tuple[1][0]",  # NEW: named_sub_modules allows recursive structures, but named_parameters does not
    }
    found_names = {name for name, _ in root.named_sub_modules()}

    assert (
        found_names == expected_names
    ), f"Missing or extra modules found. Missing: {expected_names-found_names}, Extra: {found_names-expected_names}"


def test_complex_module_set_attribute_by_name():
    root = Module()
    root.sub_module = Module()
    root.sub_module.nested_list = [Module(), {"key": Module()}]
    same_module = Module()
    root.sub_module.nested_tuple = (Module(), [same_module, same_module])

    set_attribute_by_name(root, "test_attrib", True)
    assert root.test_attrib is True
    set_attribute_by_name(root, "sub_module.test_attrib", True)
    assert root.sub_module.test_attrib is True
    set_attribute_by_name(root, "sub_module.nested_list[0].test_attrib", True)
    assert root.sub_module.nested_list[0].test_attrib is True
    set_attribute_by_name(root, "sub_module.nested_list[1]['key'].test_attrib", True)
    assert root.sub_module.nested_list[1]["key"].test_attrib is True
    set_attribute_by_name(root, "sub_module.nested_tuple[0].test_attrib", True)
    assert root.sub_module.nested_tuple[0].test_attrib is True
    set_attribute_by_name(root, "sub_module.nested_tuple[1][0].test_attrib", True)
    assert root.sub_module.nested_tuple[1][0].test_attrib is True
    assert root.sub_module.nested_tuple[1][1].test_attrib is True


class DuplicateModule(Module):
    def __init__(self):
        super().__init__()
        self.p0 = dspy.Predict("question -> answer")
        self.p1 = self.p0


def test_named_parameters_duplicate_references():
    module = DuplicateModule()
    # Only testing for whether exceptions are thrown or not
    # As Module.named_parameters() is recursive, this is mainly for catching infinite recursion
    module.named_parameters()
