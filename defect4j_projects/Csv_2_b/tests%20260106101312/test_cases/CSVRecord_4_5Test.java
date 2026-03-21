package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

public class CSVRecord_4_5Test {

    @Test
    @Timeout(8000)
    void testIsConsistent_mappingNull_returnsTrue() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        // Prepare CSVRecord instance with mapping = null
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = null;
        CSVRecord record = new CSVRecord(values, mapping, null, 1L);

        // Use reflection to invoke isConsistent method
        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);

        boolean result = (boolean) method.invoke(record);

        assertTrue(result, "When mapping is null, isConsistent should return true");
    }

    @Test
    @Timeout(8000)
    void testIsConsistent_mappingSizeEqualsValuesLength_returnsTrue() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);

        CSVRecord record = new CSVRecord(values, mapping, null, 2L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);

        boolean result = (boolean) method.invoke(record);

        assertTrue(result, "When mapping size equals values length, isConsistent should return true");
    }

    @Test
    @Timeout(8000)
    void testIsConsistent_mappingSizeNotEqualsValuesLength_returnsFalse() throws NoSuchMethodException, InvocationTargetException, IllegalAccessException {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);

        CSVRecord record = new CSVRecord(values, mapping, null, 3L);

        Method method = CSVRecord.class.getDeclaredMethod("isConsistent");
        method.setAccessible(true);

        boolean result = (boolean) method.invoke(record);

        assertFalse(result, "When mapping size does not equal values length, isConsistent should return false");
    }
}