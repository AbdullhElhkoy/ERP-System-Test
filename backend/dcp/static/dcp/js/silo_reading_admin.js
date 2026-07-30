document.addEventListener('DOMContentLoaded', function() {
    var weightInput = document.getElementById('id_represented_weight_tons');
    var plantSelect = document.getElementById('id_plant');
    var siloSelect = document.getElementById('id_silo');
    var sequenceInput = document.getElementById('id_sequence_number');
    
    if (!weightInput || !plantSelect || !sequenceInput) return;

    function getRows() {
        return document.querySelectorAll('tr.dynamic-lots, tr.form-row.dynamic-lots');
    }

    function updateRows() {
        var target = parseInt(weightInput.value);
        if (!target || target < 1) return;

        var rows = getRows();
        rows.forEach(function(row, index) {
            var lotInput = row.querySelector('input[id$="-lot_number"]');
            if (index < target) {
                row.style.display = '';
                if (lotInput) {
                    lotInput.value = index + 1;
                }
            } else {
                row.style.display = 'none';
                if (lotInput) {
                    lotInput.value = '';
                }
            }
        });
    }

    function updateSequencePreview() {
        var plantId = plantSelect.value;
        var weight = weightInput.value;
        var silo = siloSelect ? siloSelect.value : '';
        
        if (!plantId || !weight) return;

        fetch('/api/dcp/next-sequence-preview/?plant_id=' + plantId + '&weight=' + weight + '&silo=' + silo)
            .then(function(response) { return response.json(); })
            .then(function(data) {
                if (data.sample_code_preview) {
                    // إظهار كود الممثلة الكامل بالشكل المطلوب 1C(1+2+3+4)A
                    sequenceInput.value = data.sample_code_preview;
                    sequenceInput.style.backgroundColor = '#eaffea';
                    sequenceInput.style.fontWeight = 'bold';
                }
            })
            .catch(function(err) { console.log('sequence preview error', err); });
    }

    function updateAll() {
        updateRows();
        updateSequencePreview();
    }

    weightInput.addEventListener('input', updateAll);
    weightInput.addEventListener('change', updateAll);
    plantSelect.addEventListener('change', updateAll);
    if (siloSelect) {
        siloSelect.addEventListener('change', updateAll);
    }
});
