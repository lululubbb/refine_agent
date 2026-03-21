package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class CSVRecord_3_6Test {

    private Map<String, Integer> mapping;
    private String[] values;

    @BeforeEach
    void setUp() {
        mapping = new HashMap<>();
        mapping.put("header1", 0);
        mapping.put("header2", 1);
        values = new String[] { "value1", "value2" };
    }

    @Test
    @Timeout(8000)
    void testGet_WithMappingAndExistingName_ReturnsValue() throws Exception {
        CSVRecord record = createCSVRecord(values, mapping, "comment", 1L);
        String result = record.get("header1");
        assertEquals("value1", result);
    }

    @Test
    @Timeout(8000)
    void testGet_WithMappingAndNonExistingName_ReturnsNull() throws Exception {
        CSVRecord record = createCSVRecord(values, mapping, "comment", 1L);
        String result = record.get("nonexistent");
        assertNull(result);
    }

    @Test
    @Timeout(8000)
    void testGet_WithNullMapping_ThrowsIllegalStateException() throws Exception {
        CSVRecord record = createCSVRecord(values, null, "comment", 1L);
        IllegalStateException thrown = assertThrows(IllegalStateException.class, () -> record.get("header1"));
        assertEquals("No header mapping was specified, the record values can't be accessed by name", thrown.getMessage());
    }

    // Helper method to instantiate CSVRecord via reflection since constructor is package-private
    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber)
            throws NoSuchMethodException, IllegalAccessException, InvocationTargetException, InstantiationException {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance((Object) values, mapping, comment, recordNumber);
    }
}