package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.Map;
import java.util.HashMap;

class CSVRecord_8_5Test {

    @Test
    @Timeout(8000)
    void testValues() throws Exception {
        String[] inputValues = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        String comment = "comment";
        long recordNumber = 123L;

        // Use the package-private constructor with all arguments via reflection
        CSVRecord record;
        try {
            record = new CSVRecord(inputValues, mapping, comment, recordNumber);
        } catch (NoSuchMethodError | NoSuchMethodException | IllegalAccessException e) {
            // fallback: use reflection to invoke package-private constructor
            var constructor = CSVRecord.class.getDeclaredConstructor(String[].class, Map.class, String.class, long.class);
            constructor.setAccessible(true);
            record = constructor.newInstance(inputValues, mapping, comment, recordNumber);
        }

        // Access the package-private method 'values' via reflection
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);
        String[] result = (String[]) valuesMethod.invoke(record);

        assertArrayEquals(inputValues, result);
    }
}