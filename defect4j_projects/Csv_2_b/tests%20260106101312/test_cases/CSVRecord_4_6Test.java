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

public class CSVRecord_4_6Test {

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingIsNull() throws Exception {
        // Prepare CSVRecord with mapping = null
        String[] values = new String[] {"a", "b"};
        Map<String, Integer> mapping = null;
        String comment = "comment";
        long recordNumber = 1L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);

        boolean result = (boolean) isConsistentMethod.invoke(record);

        assertTrue(result, "Expected true when mapping is null");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeEqualsValuesLength() throws Exception {
        // Prepare CSVRecord with mapping size == values length
        String[] values = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        String comment = null;
        long recordNumber = 2L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);

        boolean result = (boolean) isConsistentMethod.invoke(record);

        assertTrue(result, "Expected true when mapping size equals values length");
    }

    @Test
    @Timeout(8000)
    public void testIsConsistent_mappingSizeNotEqualsValuesLength() throws Exception {
        // Prepare CSVRecord with mapping size != values length
        String[] values = new String[] {"a", "b", "c", "d"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        String comment = "comment";
        long recordNumber = 3L;

        Constructor<CSVRecord> constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
        constructor.setAccessible(true);
        CSVRecord record = constructor.newInstance((Object) values, mapping, comment, recordNumber);

        Method isConsistentMethod = CSVRecord.class.getDeclaredMethod("isConsistent");
        isConsistentMethod.setAccessible(true);

        boolean result = (boolean) isConsistentMethod.invoke(record);

        assertFalse(result, "Expected false when mapping size does not equal values length");
    }
}