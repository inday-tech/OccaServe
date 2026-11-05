(function () {
    let locationBoundariesPromise;

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

    function composeAddress({ street = '', landmark = '', barangay = '', municipality = '', province = '' } = {}) {
        const parts = [street, landmark, barangay, municipality, province]
            .map(part => String(part || '').trim())
            .filter(Boolean);
        return parts.filter((part, index) =>
            parts.findIndex(candidate => candidate.toLowerCase() === part.toLowerCase()) === index
        ).join(', ');
    }

    function loadLocationBoundaries() {
        if (!locationBoundariesPromise) {
            locationBoundariesPromise = fetch('/static/data/ph_location_boundaries.json', {
                credentials: 'same-origin'
            }).then(response => {
                if (!response.ok) throw new Error('Location boundary data could not be loaded.');
                return response.json();
            }).then(data => {
                if (!Array.isArray(data.land) || !Array.isArray(data.water_polygons) || !Array.isArray(data.river_lines)) {
                    throw new Error('Location boundary data is invalid.');
                }
                return data;
            }).catch(error => {
                locationBoundariesPromise = null;
                throw error;
            });
        }
        return locationBoundariesPromise;
    }

    function ringContains(longitude, latitude, ring) {
        let inside = false;
        for (let index = 0; index < ring.length; index += 1) {
            const [x1, y1] = ring[index];
            const [x2, y2] = ring[(index + 1) % ring.length];
            const cross = (longitude - x1) * (y2 - y1) - (latitude - y1) * (x2 - x1);
            if (
                Math.abs(cross) <= 1e-10
                && longitude >= Math.min(x1, x2) - 1e-10
                && longitude <= Math.max(x1, x2) + 1e-10
                && latitude >= Math.min(y1, y2) - 1e-10
                && latitude <= Math.max(y1, y2) + 1e-10
            ) return true;
            if ((y1 > latitude) !== (y2 > latitude)) {
                const crossingLongitude = (x2 - x1) * (latitude - y1) / (y2 - y1) + x1;
                if (longitude < crossingLongitude) inside = !inside;
            }
        }
        return inside;
    }

    function polygonContains(longitude, latitude, rings) {
        return Boolean(rings?.length)
            && ringContains(longitude, latitude, rings[0])
            && !rings.slice(1).some(hole => ringContains(longitude, latitude, hole));
    }

    function geometryContains(geometry, longitude, latitude) {
        if (geometry.type === 'Polygon') return polygonContains(longitude, latitude, geometry.coordinates);
        if (geometry.type === 'MultiPolygon') {
            return geometry.coordinates.some(polygon => polygonContains(longitude, latitude, polygon));
        }
        if (geometry.type === 'GeometryCollection') {
            return geometry.geometries.some(item => geometryContains(item, longitude, latitude));
        }
        return false;
    }

    function pointNearLine(longitude, latitude, line, bufferMeters = 30) {
        const metersPerDegree = 111320;
        const longitudeScale = Math.cos(latitude * Math.PI / 180);
        const pointX = longitude * longitudeScale * metersPerDegree;
        const pointY = latitude * metersPerDegree;
        for (let index = 0; index < line.length - 1; index += 1) {
            const x1 = line[index][0] * longitudeScale * metersPerDegree;
            const y1 = line[index][1] * metersPerDegree;
            const x2 = line[index + 1][0] * longitudeScale * metersPerDegree;
            const y2 = line[index + 1][1] * metersPerDegree;
            const dx = x2 - x1;
            const dy = y2 - y1;
            const lengthSquared = dx * dx + dy * dy;
            const projection = lengthSquared === 0
                ? 0
                : Math.max(0, Math.min(1, ((pointX - x1) * dx + (pointY - y1) * dy) / lengthSquared));
            const distanceX = pointX - (x1 + projection * dx);
            const distanceY = pointY - (y1 + projection * dy);
            if (distanceX * distanceX + distanceY * distanceY <= bufferMeters * bufferMeters) return true;
        }
        return false;
    }

    function geometryNearLine(geometry, longitude, latitude) {
        if (geometry.type === 'LineString') return pointNearLine(longitude, latitude, geometry.coordinates);
        if (geometry.type === 'MultiLineString') {
            return geometry.coordinates.some(line => pointNearLine(longitude, latitude, line));
        }
        if (geometry.type === 'GeometryCollection') {
            return geometry.geometries.some(item => geometryNearLine(item, longitude, latitude));
        }
        return false;
    }

    async function isValidPhilippineLandCoordinate(latitude, longitude) {
        const lat = Number(latitude);
        const lng = Number(longitude);
        if (!Number.isFinite(lat) || !Number.isFinite(lng)
            || lat < 4.2 || lat > 21.6 || lng < 116.7 || lng > 127.2) return false;
        const boundaries = await loadLocationBoundaries();
        return boundaries.land.some(geometry => geometryContains(geometry, lng, lat))
            && !boundaries.water_polygons.some(geometry => geometryContains(geometry, lng, lat))
            && !boundaries.river_lines.some(geometry => geometryNearLine(geometry, lng, lat));
    }

    window.OccaServeLocationAddress = {
        parseResults,
        composeAddress,
        isValidPhilippineLandCoordinate
    };
})();
