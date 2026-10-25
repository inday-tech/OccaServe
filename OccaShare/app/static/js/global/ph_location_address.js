(function () {
    function addressComponent(result, ...types) {
        const components = result?.address_components || [];
        for (const type of types) {
            const component = components.find(item => item.types.includes(type));
            if (component?.long_name) return component.long_name;
        }
        return '';
    }

    function parseResult(result) {
        const province = addressComponent(result, 'administrative_area_level_1');
        const city = addressComponent(result, 'locality', 'postal_town', 'administrative_area_level_2');
        const barangay = addressComponent(
            result,
            'administrative_area_level_4',
            'sublocality_level_1',
            'sublocality_level_2',
            'sublocality_level_3',
            'administrative_area_level_3',
            'neighborhood',
            'sublocality'
        );
        return { province, city, barangay };
    }

    function parseResults(results) {
        return (results || [])
            .map(result => ({ address: parseResult(result) }))
            .filter(candidate => candidate.address.province || candidate.address.city || candidate.address.barangay)
            .sort((a, b) => {
                const score = address => Number(Boolean(address.barangay)) * 100 +
                    Number(Boolean(address.city)) * 20 +
                    Number(Boolean(address.province)) * 5;
                return score(b.address) - score(a.address);
            })[0]?.address || null;
    }

    function composeAddress({ landmark = '', barangay = '', municipality = '', province = '' } = {}) {
        const parts = [landmark, barangay, municipality, province]
            .map(part => String(part || '').trim())
            .filter(Boolean);
        return parts.filter((part, index) =>
            parts.findIndex(candidate => candidate.toLowerCase() === part.toLowerCase()) === index
        ).join(', ');
    }

    window.OccaServeLocationAddress = { parseResults, composeAddress };
})();
