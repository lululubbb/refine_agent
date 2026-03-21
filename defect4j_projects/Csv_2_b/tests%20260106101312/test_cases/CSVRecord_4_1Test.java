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

public class CSVRecord_4_1Test {

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingNull() throws Exception {
        // Create CSVRecord with mapping = null
        String[] values = new String[] { "a", "b", "c" };
        CSVRecord record = createCSVRecord(values, null, "comment", 1L);

        // Use reflection to invoke isConsistent method
        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        assertTrue(result, "Expected isConsistent to return true when mapping is null");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        // mapping size == values.length
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("one", 0);
        mapping.put("two", 1);
        mapping.put("three", 2);

        CSVRecord record = createCSVRecord(values, mapping, "comment", 1L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        assertTrue(result, "Expected isConsistent to return true when mapping size equals values length");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        // mapping size != values.length
        String[] values = new String[] { "a", "b", "c" };
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("one", 0);
        mapping.put("two", 1);

        CSVRecord record = createCSVRecord(values, mapping, "comment", 1L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);
        boolean result = (boolean) method.invoke(record);

        assertFalse(result, "Expected isConsistent to return false when mapping size does not equal values length");
    }

    private CSVRecord createCSVRecord(String[] values, Map<String, Integer> mapping, String comment, long recordNumber) throws Exception {
        Class<CSVRecord> clazz = CSVRecord.class;
        Constructor<CSVRecord> ctor = clazz.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        ctor.setAccessible(true);
        return ctor.newInstance((Object) values, mapping, comment, recordNumber);
    }
}