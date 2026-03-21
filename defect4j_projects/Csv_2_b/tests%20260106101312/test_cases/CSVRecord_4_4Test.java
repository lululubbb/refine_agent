package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;

import java.lang.reflect.Constructor;
import java.lang.reflect.InvocationTargetException;
import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

import org.junit.jupiter.api.Test;

class CSVRecord_4_4Test {

    @Test
    @Timeout(8000)
    void testIsConsistent_mappingNull() throws NoSuchMethodException, InvocationTargetException, InstantiationException, IllegalAccessException {
        // Prepare values array (can be empty or any)
        String[] values = new String[] {"a", "b"};

        // mapping is null
        Map<String, Integer> mapping = null;

        // Create CSVRecord instance via constructor using reflection
        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 1L);

        // Use reflection to invoke isConsistent method
        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);

        boolean result = (boolean) isConsistentMethod.invoke(record);

        assertTrue(result, "When mapping is null, isConsistent should return true");
    }

    @Test
    @Timeout(8000)
    void testIsConsistent_mappingSizeEqualsValuesLength() throws NoSuchMethodException, InvocationTargetException, InstantiationException, IllegalAccessException {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, "comment", 5L);

        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);

        boolean result = (boolean) isConsistentMethod.invoke(record);

        assertTrue(result, "When mapping size equals values length, isConsistent should return true");
    }

    @Test
    @Timeout(8000)
    void testIsConsistent_mappingSizeNotEqualsValuesLength() throws NoSuchMethodException, InvocationTargetException, InstantiationException, IllegalAccessException {
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, null, 10L);

        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);

        boolean result = (boolean) isConsistentMethod.invoke(record);

        assertFalse(result, "When mapping size does not equal values length, isConsistent should return false");
    }
}