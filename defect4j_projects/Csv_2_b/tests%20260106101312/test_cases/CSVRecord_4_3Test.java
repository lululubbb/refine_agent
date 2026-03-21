package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

public class CSVRecord_4_3Test {

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance(values, mapping, comment, recordNumber);
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingNull() throws Exception {
        String[] values = new String[] {"a", "b"};
        Map<String, Integer> mapping = null;
        CSVRecord record = createCSVRecord(values, mapping, null, 1L);

        boolean result = record.isConsistent();

        assertTrue(result, "When mapping is null, isConsistent should return true");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        CSVRecord record = createCSVRecord(values, mapping, null, 2L);

        boolean result = record.isConsistent();

        assertTrue(result, "When mapping size equals values length, isConsistent should return true");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        // mapping size 2, values length 3
        CSVRecord record = createCSVRecord(values, mapping, null, 3L);

        boolean result = record.isConsistent();

        assertFalse(result, "When mapping size does not equal values length, isConsistent should return false");
    }
}