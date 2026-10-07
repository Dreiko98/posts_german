from app.evidence import restrict_generated_links


def test_generated_citations_require_saved_provenance():
    data = {
        "body": '<p><a href="https://verified.example/doc/#section">Fuente</a> y <a href="https://invented.example/claim">cita inventada</a></p>'
    }
    cleaned, warnings = restrict_generated_links(
        data, ["https://verified.example/doc/"]
    )
    assert 'href="https://verified.example/doc/#section"' in cleaned["body"]
    assert (
        "invented.example" not in cleaned["body"]
        and "cita inventada" in cleaned["body"]
    )
    assert len(warnings) == 1
