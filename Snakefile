rule download_data:
    output:
        temporary("epi_cpsbasic_2022.feather"),
    shell:
        "wget https://microdata.epi.org/epi_cpsbasic.tar.gz -O - | tar -zxvf - epi_cpsbasic_2022.feather"


rule prepare_data:
    input:
        *rules.download_data.output,
    output:
        "input_data/data.feather",
    script:
        "scripts/prepare_data.py"


rule extract_metadata:
    input:
        *rules.prepare_data.output,
    output:
        "input_data/data.json",
    script:
        "scripts/extract_metadata.py"


rule bundle:
    input:
        "competition.yaml",
        "logo.png",
        "pages/terms.md",
        "pages/welcome.md",
        "input_data/data.feather",
        "input_data/data.json",
        "ingestion_program/metadata.yaml",
        "ingestion_program/ingestion.py",
        # "reference_data",
        "scoring_program",
        "scoring_program/metadata.yaml",
        "scoring_program/scoring.py",
        "solution_example/taskmaster.py",
    output:
        "bundle.zip",
    shell:
        "zip {output} {input}"


rule test_ingestion:
    input:
        input_data="input_data",
        submission="solution_example",
        program="ingestion_program/ingestion.py"
    output:
        "output/threat_model.pkl",
        "output/attacks.pkl",
    container: "docker://ghcr.io/lbeziaud/docker-tapas:main"
    shell:
        "python {input.program} --input {input.input_data} --output output --submission {input.submission}"


rule test_scoring:
    input:
        *rules.test_ingestion.output,
        program="scoring_program/scoring.py"
    output:
        "output/scores.json",
    container: "docker://ghcr.io/lbeziaud/docker-tapas:main"
    shell:
        "python {input.program} --input output --output output"


rule test:
    input:
        rules.test_ingestion.output,
        rules.test_scoring.output,
