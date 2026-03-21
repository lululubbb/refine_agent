package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

public class CSVRecord_3_5Test {

    private CSVRecord csvRecord;
    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    public void setUp() throws Exception {
        values = new String[] {"val0", "val1", "val2"};
        mapping = new HashMap<>();
        mapping.put("key0", 0);
        mapping.put("key1", 1);
        mapping.put("key2", 2);

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        csvRecord = constructor.newInstance((Object) values, mapping, null, 1L);
    }

    @Test
    @Timeout(8000)
    public void testGet_WithValidName_ReturnsValue() {
        assertEquals("val0", csvRecord.get("key0"));
        assertEquals("val1", csvRecord.get("key1"));
        assertEquals("val2", csvRecord.get("key2"));
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNameNotInMapping_ReturnsNull() {
        assertNull(csvRecord.get("nonexistent"));
    }

    @Test
    @Timeout(8000)
    public void testGet_WithNullMapping_ThrowsIllegalStateException() throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord recordWithNullMapping = constructor.newInstance((Object) values, null, null, 1L);

        IllegalStateException exception = assertThrows(IllegalStateException.class, () -> recordWithNullMapping.get("key0"));
        assertEquals("No header mapping was specified, the record values can't be accessed by name", exception.getMessage());
    }

    @Test
    @Timeout(8000)
    public void testGet_WithMappingIndexOutOfBounds_ThrowsArrayIndexOutOfBoundsException() throws Exception {
        Map<String, Integer> badMapping = new HashMap<>();
        badMapping.put("badKey", values.length); // index == values.length (out of bounds)

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, badMapping, null, 1L);

        assertThrows(ArrayIndexOutOfBoundsException.class, () -> record.get("badKey"));
    }
}