package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

public class CSVRecord_4_2Test {

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingNull() throws Exception {
        // Prepare values array
        String[] values = new String[] {"a", "b", "c"};

        // mapping null
        Map<String, Integer> mapping = null;

        // Create CSVRecord instance via constructor using reflection since constructor is package-private
        CSVRecord record = createCSVRecord(values, mapping, "comment", 1L);

        // Use reflection to invoke isConsistent method
        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        assertTrue(result, "Expected isConsistent to return true when mapping is null");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);

        CSVRecord record = createCSVRecord(values, mapping, "comment", 2L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        assertTrue(result, "Expected isConsistent to return true when mapping size equals values length");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);

        CSVRecord record = createCSVRecord(values, mapping, "comment", 3L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        assertFalse(result, "Expected isConsistent to return false when mapping size does not equal values length");
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        return constructor.newInstance((Object) values, mapping, comment, recordNumber);
    }
}