package org.apache.commons.csv;
import org.junit.jupiter.api.Timeout;
import java.io.Serializable;
import java.util.Arrays;
import java.util.Iterator;

import static org.junit.jupiter.api.Assertions.*;
import org.junit.jupiter.api.Test;

import java.lang.reflect.Method;
import java.util.HashMap;
import java.util.Map;

public class CSVRecord_8_6Test {

    @Test
    @Timeout(8000)
    void testValuesMethod() throws Exception {
        // Prepare test data
        String[] expectedValues = new String[] {"a", "b", "c"};
        Map<String, Integer> mapping = new HashMap<>();
        mapping.put("col1", 0);
        mapping.put("col2", 1);
        mapping.put("col3", 2);
        String comment = "comment";
        long recordNumber = 123L;

        // Create instance of CSVRecord using constructor
        CSVRecord record = new CSVRecord(expectedValues, mapping, comment, recordNumber);

        // Use reflection to access the package-private values() method
        Method valuesMethod = CSVRecord.class.getDeclaredMethod("values");
        valuesMethod.setAccessible(true);

        // Invoke the values() method
        String[] actualValues = (String[]) valuesMethod.invoke(record);

        // Assert the returned array is the same as the one passed in constructor
        assertArrayEquals(expectedValues, actualValues);
    }
}